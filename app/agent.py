import operator
import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ResearchTask

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", google_api_key=os.getenv("GEMINI_API_KEY")
)

tavily = TavilySearchResults(max_results=3, tavily_api_key=os.getenv("TAVILY_API_KEY"))

llm_with_tools = llm.bind_tools([tavily])


class ResearchState(TypedDict):
    task_id: str
    prompt: str
    messages: Annotated[list[BaseMessage], operator.add]
    report: str


async def researcher_node(state: ResearchState) -> ResearchState:
    response = await llm_with_tools.ainvoke(
        [
            HumanMessage(
                content=(
                    f"Research this topic thoroughly using web search. "
                    f"Search for at least 2-3 different angles:\n{state['prompt']}"
                )
            )
        ]
    )
    return {**state, "messages": [response]}


async def writer_node(state: ResearchState) -> ResearchState:
    research_content = "\n".join(
        [
            msg.content
            for msg in state["messages"]
            if hasattr(msg, "content") and msg.content
        ]
    )
    response = await llm.ainvoke(
        f"Based on this research:\n{research_content}"
        f"\n\nWrite a clean, structured, detailed report about: {state['prompt']}"
    )
    return {**state, "report": response.content}


def should_use_tools(state: ResearchState) -> str:
    last_message = state["messages"][-1]
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"
    return "writer"


def build_graph():
    graph = StateGraph(ResearchState)

    tool_node = ToolNode([tavily])

    graph.add_node("researcher", researcher_node)
    graph.add_node("tools", tool_node)
    graph.add_node("writer", writer_node)

    graph.set_entry_point("researcher")

    graph.add_conditional_edges(
        "researcher", should_use_tools, {"tools": "tools", "writer": "writer"}
    )

    graph.add_edge("tools", "writer")
    graph.add_edge("writer", END)

    return graph.compile()


async def run_agent(task_id: str, prompt: str, db: AsyncSession):
    from sqlalchemy import select

    result = await db.execute(select(ResearchTask).where(ResearchTask.id == task_id))
    task = result.scalar_one()
    task.status = "processing"
    await db.commit()

    graph = build_graph()
    final_state = await graph.ainvoke(
        {"task_id": task_id, "prompt": prompt, "messages": [], "report": ""}
    )

    task.result = final_state["report"]
    task.status = "done"
    await db.commit()

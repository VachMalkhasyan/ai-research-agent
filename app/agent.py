from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import ResearchTask
from typing import TypedDict
from dotenv import load_dotenv
import os

load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

class ResearchState(TypedDict):
    task_id: str
    prompt: str
    research: str
    report: str


async def researcher_node(state: ResearchState) -> ResearchState:
    response = await llm.ainvoke(
        f"Research the following topic thoroughly and list key findings:\n{state['prompt']}"
    )
    return {**state, "research": response.content}

async def writer_node(state: ResearchState) -> ResearchState:
    response = await llm.ainvoke(
        f"Based on this research:\n{state['research']}\n\nWrite a clean, structured report."
    )
    return {**state, "report": response.content}

def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)

    graph.set_entry_point("researcher")
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", END)

    return graph.compile()

async def run_agent(task_id: str, prompt: str, db: AsyncSession):
    from sqlalchemy import select

    result = await db.execute(select(ResearchTask).where(ResearchTask.id == task_id))
    task = result.scalar_one()
    task.status = "processing"
    await db.commit()

    graph = build_graph()
    final_state = await graph.ainvoke({
        "task_id": task_id,
        "prompt": prompt,
        "research": "",
        "report": ""
    })

    task.result = final_state["report"]
    task.status = "done"
    await db.commit()
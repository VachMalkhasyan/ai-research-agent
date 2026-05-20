from fastapi import FastAPI, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db, engine, Base
from app.models import ResearchTask
from app.agent import run_agent
from pydantic import BaseModel
import uuid

app = FastAPI()

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

class ResearchRequest(BaseModel):
    prompt: str

@app.post("/research", status_code=202)
async def create_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    task_id = str(uuid.uuid4())

    task = ResearchTask(id=task_id, prompt=request.prompt, status="pending")
    db.add(task)
    await db.commit()

    background_tasks.add_task(run_agent, task_id, request.prompt, db)

    return {"task_id": task_id, "status": "pending"}

@app.get("/research/{task_id}")
async def get_research(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ResearchTask).where(ResearchTask.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        return {"error": "Task not found"}

    return {
        "task_id": task.id,
        "status": task.status,
        "prompt": task.prompt,
        "result": task.result
    }
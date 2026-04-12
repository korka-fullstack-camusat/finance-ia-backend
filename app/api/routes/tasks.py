"""Routes tâches — 100% async."""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from app.models.task import Task, TaskFrequency, TaskStatus
from app.agent.orchestrator import stream_task_execution

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskOut(BaseModel):
    id: str
    name: str
    description: str
    task_type: str
    is_auto: bool
    frequency: str
    status: str
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class FrequencyUpdate(BaseModel):
    frequency: TaskFrequency


@router.get("", response_model=List[TaskOut])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).order_by(Task.created_at))
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    return task


@router.patch("/{task_id}/toggle", response_model=TaskOut)
async def toggle_task(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    task.is_auto = not task.is_auto
    await db.commit()
    await db.refresh(task)
    return task


@router.patch("/{task_id}/frequency", response_model=TaskOut)
async def update_frequency(
    task_id: str, body: FrequencyUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    task.frequency = body.frequency
    await db.commit()
    await db.refresh(task)
    return task


@router.post("/{task_id}/run")
async def run_task_manual(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    if task.status == TaskStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Tâche déjà en cours")

    async def generator():
        async for chunk in stream_task_execution(task, db):
            yield chunk

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{task_id}/status")
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    return {"id": task.id, "status": task.status, "last_run": task.last_run}

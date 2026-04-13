"""Routes tâches — sync CRUD + async SSE streaming."""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select

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
def list_tasks(db: Session = Depends(get_db)):
    return db.execute(select(Task).order_by(Task.created_at)).scalars().all()


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    return task


@router.patch("/{task_id}/toggle", response_model=TaskOut)
def toggle_task(task_id: str, db: Session = Depends(get_db)):
    task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    task.is_auto = not task.is_auto
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}/frequency", response_model=TaskOut)
def update_frequency(task_id: str, body: FrequencyUpdate, db: Session = Depends(get_db)):
    task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    task.frequency = body.frequency
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/run")
async def run_task_manual(task_id: str, db: Session = Depends(get_db)):
    """Lance une tâche manuellement — streaming SSE async."""
    task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
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
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    return {"id": task.id, "status": task.status, "last_run": task.last_run}

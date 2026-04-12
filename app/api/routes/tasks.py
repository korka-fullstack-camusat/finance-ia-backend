"""Routes CRUD pour les tâches financières."""
import asyncio
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from app.models.task import Task, TaskFrequency, TaskStatus, TaskType
from app.agent.orchestrator import stream_task_execution

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# --- Schemas Pydantic ---

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


# --- Endpoints ---

@router.get("", response_model=List[TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    """Liste toutes les tâches financières."""
    tasks = db.query(Task).order_by(Task.created_at).all()
    return tasks


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")
    return task


@router.patch("/{task_id}/toggle", response_model=TaskOut)
def toggle_task(task_id: str, db: Session = Depends(get_db)):
    """Bascule entre mode AUTO et MANUEL."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    task.is_auto = not task.is_auto
    db.commit()
    db.refresh(task)
    return task


@router.patch("/{task_id}/frequency", response_model=TaskOut)
def update_frequency(task_id: str, body: FrequencyUpdate, db: Session = Depends(get_db)):
    """Change la fréquence d'exécution d'une tâche."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    task.frequency = body.frequency
    db.commit()
    db.refresh(task)
    return task


@router.post("/{task_id}/run")
async def run_task_manual(task_id: str, db: Session = Depends(get_db)):
    """Lance manuellement une tâche (réponse SSE streaming)."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    if task.status == TaskStatus.RUNNING:
        raise HTTPException(status_code=409, detail="Tâche déjà en cours d'exécution")

    async def event_generator():
        async for chunk in stream_task_execution(task, db):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{task_id}/status")
def get_task_status(task_id: str, db: Session = Depends(get_db)):
    """Retourne le statut actuel d'une tâche."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Tâche introuvable")

    return {
        "id": task.id,
        "status": task.status,
        "last_run": task.last_run,
        "next_run": task.next_run,
    }

"""Routes résultats d'analyse — 100% async."""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from app.models.task import TaskResult

router = APIRouter(prefix="/api/results", tags=["results"])


class ResultOut(BaseModel):
    id: str
    task_id: str
    content: str
    summary: str
    duration: float
    triggered_by: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[ResultOut])
async def list_results(
    limit: int = 20,
    task_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(TaskResult).order_by(desc(TaskResult.created_at)).limit(limit)
    if task_id:
        query = query.where(TaskResult.task_id == task_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{task_id}/latest", response_model=ResultOut)
async def get_latest_result(task_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(TaskResult)
        .where(TaskResult.task_id == task_id)
        .order_by(desc(TaskResult.created_at))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Aucun résultat pour cette tâche")
    return row

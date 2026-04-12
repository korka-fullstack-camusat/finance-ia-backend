"""Routes pour récupérer les résultats d'analyse."""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

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
def list_results(
    limit: int = 20,
    task_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Historique des résultats d'analyse."""
    query = db.query(TaskResult)
    if task_id:
        query = query.filter(TaskResult.task_id == task_id)
    results = query.order_by(TaskResult.created_at.desc()).limit(limit).all()
    return results


@router.get("/{task_id}/latest", response_model=ResultOut)
def get_latest_result(task_id: str, db: Session = Depends(get_db)):
    """Dernier résultat d'une tâche donnée."""
    result = (
        db.query(TaskResult)
        .filter(TaskResult.task_id == task_id)
        .order_by(TaskResult.created_at.desc())
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Aucun résultat pour cette tâche")
    return result

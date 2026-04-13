"""Routes notifications — sync."""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc, update
from sqlalchemy.orm import Session

from database import get_db
from app.models.notification import Notification

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


class NotificationOut(BaseModel):
    id: str
    task_id: Optional[str] = None
    task_name: str
    message: str
    channel: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=List[NotificationOut])
def list_notifications(limit: int = 50, db: Session = Depends(get_db)):
    return db.execute(
        select(Notification)
        .where(Notification.is_read == False)
        .order_by(desc(Notification.created_at))
        .limit(limit)
    ).scalars().all()


@router.delete("/{notif_id}")
def mark_read(notif_id: str, db: Session = Depends(get_db)):
    notif = db.execute(select(Notification).where(Notification.id == notif_id)).scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    notif.is_read = True
    db.commit()
    return {"message": "Notification marquée comme lue"}


@router.delete("")
def clear_all(db: Session = Depends(get_db)):
    db.execute(update(Notification).values(is_read=True))
    db.commit()
    return {"message": "Toutes les notifications marquées comme lues"}

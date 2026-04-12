"""Routes pour les notifications."""
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
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

from typing import Optional


@router.get("", response_model=List[NotificationOut])
def list_notifications(limit: int = 50, db: Session = Depends(get_db)):
    """Liste des notifications, les plus récentes en premier."""
    notifs = (
        db.query(Notification)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )
    return notifs


@router.delete("/{notif_id}")
def mark_read(notif_id: str, db: Session = Depends(get_db)):
    """Marque une notification comme lue (supprime de la liste)."""
    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification introuvable")

    notif.is_read = True
    db.commit()
    return {"message": "Notification marquée comme lue"}


@router.delete("")
def clear_all_notifications(db: Session = Depends(get_db)):
    """Marque toutes les notifications comme lues."""
    db.query(Notification).update({"is_read": True})
    db.commit()
    return {"message": "Toutes les notifications marquées comme lues"}

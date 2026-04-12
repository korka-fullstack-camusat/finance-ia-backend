"""Routes notifications — 100% async."""
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

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
async def list_notifications(limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Notification)
        .where(Notification.is_read == False)
        .order_by(desc(Notification.created_at))
        .limit(limit)
    )
    return result.scalars().all()


@router.delete("/{notif_id}")
async def mark_read(notif_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Notification).where(Notification.id == notif_id)
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    notif.is_read = True
    await db.commit()
    return {"message": "Notification marquée comme lue"}


@router.delete("")
async def clear_all(db: AsyncSession = Depends(get_db)):
    await db.execute(update(Notification).values(is_read=True))
    await db.commit()
    return {"message": "Toutes les notifications marquées comme lues"}

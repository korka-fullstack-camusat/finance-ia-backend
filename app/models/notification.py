import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text
from database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, nullable=True)
    task_name = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(String, default="system")  # email, slack, system
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

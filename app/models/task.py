import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, Enum, ForeignKey, Float
from sqlalchemy.orm import relationship
from database import Base


class TaskType(str, enum.Enum):
    REPORTING = "reporting"
    RECONCILIATION = "reconciliation"
    KPI = "kpi"
    FORECAST = "forecast"
    ANOMALY = "anomaly"
    AUDIT = "audit"


class TaskFrequency(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class TaskStatus(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    task_type = Column(Enum(TaskType), nullable=False)
    is_auto = Column(Boolean, default=True)
    frequency = Column(Enum(TaskFrequency), default=TaskFrequency.DAILY)
    status = Column(Enum(TaskStatus), default=TaskStatus.IDLE)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    results = relationship("TaskResult", back_populates="task", cascade="all, delete-orphan")


class TaskResult(Base):
    __tablename__ = "task_results"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    content = Column(Text, nullable=False)
    summary = Column(Text, default="")
    duration = Column(Float, default=0.0)
    triggered_by = Column(String, default="auto")  # auto | manual
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="results")

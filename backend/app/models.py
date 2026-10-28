from datetime import datetime, timezone
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
import uuid

def now_iso(): return datetime.now(timezone.utc).isoformat()
class Workflow(Base):
    __tablename__ = "workflows"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso, nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
class TaskRun(Base):
    __tablename__ = "task_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workflow_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    task_id: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    output: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    error: Mapped[str] = mapped_column(Text, default="", nullable=False)
class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    workflow_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    task_id: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String(40), default=now_iso, nullable=False)

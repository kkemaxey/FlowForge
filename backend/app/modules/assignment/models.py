"""Assignment history table. Draft by Kendyn for the simulator and exception flow; Kanayo to review.

Append-only: a row is inserted when a task is given to a worker and only ever
closed (ended_at + outcome) afterwards, never reopened or deleted.
"""
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, Timestamp, utcnow

ASSIGNMENT_OUTCOMES = ("completed", "failed", "reassigned")


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(Timestamp)
    # Null while the assignment is active.
    outcome: Mapped[str | None] = mapped_column(String(16))
    version: Mapped[int] = mapped_column(Integer, default=1)

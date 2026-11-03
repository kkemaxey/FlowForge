"""Assignment history: one row per time a task was handed to a worker."""
import enum
from datetime import datetime

from sqlalchemy import Computed, Enum, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigId, Timestamp3, utcnow


class AssignmentSource(str, enum.Enum):
    scheduler = "scheduler"
    supervisor = "supervisor"


class AssignmentOutcome(str, enum.Enum):
    completed = "completed"
    reassigned = "reassigned"
    failed = "failed"
    cancelled = "cancelled"


class Assignment(Base):
    __tablename__ = "assignments"
    __table_args__ = (
        Index("assignments_worker_id_assigned_at_index", "worker_id", "assigned_at"),
        Index("assignments_task_id_index", "task_id"),
        UniqueConstraint("active_task_id", name="uq_one_open_per_task"),
        UniqueConstraint("active_worker_id", name="uq_one_open_per_worker"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    task_id: Mapped[int] = mapped_column(BigId, ForeignKey("tasks.id"))
    worker_id: Mapped[int] = mapped_column(Integer, ForeignKey("workers.id"))
    source: Mapped[AssignmentSource] = mapped_column(
        Enum(AssignmentSource, name="assignment_source", values_callable=lambda e: [m.value for m in e])
    )
    algorithm: Mapped[str | None] = mapped_column(String(32))
    # What the assigner minimised for this pairing (Manhattan distance for greedy_v1).
    score: Mapped[float | None] = mapped_column(Float)
    assigned_at: Mapped[datetime] = mapped_column(Timestamp3, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(Timestamp3)
    ended_at: Mapped[datetime | None] = mapped_column(Timestamp3)
    outcome: Mapped[AssignmentOutcome | None] = mapped_column(
        Enum(AssignmentOutcome, name="assignment_outcome", values_callable=lambda e: [m.value for m in e])
    )

    # MySQL has no partial unique indexes. These generated columns hold the id only while the
    # assignment is open (NULL once ended_at is set), so the unique keys allow at most one open
    # assignment per task and per worker. Many NULLs are allowed. CASE works on MySQL and SQLite.
    active_task_id: Mapped[int | None] = mapped_column(
        BigId, Computed("CASE WHEN ended_at IS NULL THEN task_id END", persisted=True)
    )
    active_worker_id: Mapped[int | None] = mapped_column(
        Integer, Computed("CASE WHEN ended_at IS NULL THEN worker_id END", persisted=True)
    )

"""Simulation runs and exceptions. Base versions per the database design; extend here."""
import enum
from datetime import datetime

from sqlalchemy import Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigId, Timestamp3, utcnow


class SimRun(Base):
    """Labels one simulator run. Metrics come from events/assignments filtered by run_id."""

    __tablename__ = "sim_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    algorithm: Mapped[str] = mapped_column(String(32))
    seed: Mapped[int] = mapped_column(Integer)
    order_rate: Mapped[float] = mapped_column(Float)  # orders per minute
    started_at: Mapped[datetime] = mapped_column(Timestamp3, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(Timestamp3)


class ExceptionType(str, enum.Enum):
    stockout = "stockout"
    jam = "jam"
    worker_down = "worker_down"


class TaskException(Base):
    """A stockout, jam, or worker-down incident. Open while resolved_at IS NULL."""

    __tablename__ = "exceptions"
    __table_args__ = (Index("exceptions_resolved_at_index", "resolved_at"),)

    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    task_id: Mapped[int] = mapped_column(BigId, ForeignKey("tasks.id"))
    assignment_id: Mapped[int | None] = mapped_column(BigId, ForeignKey("assignments.id"))
    run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sim_runs.id"))
    type: Mapped[ExceptionType] = mapped_column(
        Enum(ExceptionType, name="exception_type", values_callable=lambda e: [m.value for m in e])
    )
    # For a stockout: how many units the picker actually found in the bin.
    qty_found: Mapped[int | None] = mapped_column(Integer)
    # The bin where the problem happened, and the bin the task moved to (NULL if it didn't move).
    from_location_id: Mapped[int] = mapped_column(Integer, ForeignKey("locations.id"))
    rerouted_to_location_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("locations.id"))
    opened_at: Mapped[datetime] = mapped_column(Timestamp3, default=utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(Timestamp3)

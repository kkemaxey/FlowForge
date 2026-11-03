"""Append-only event log. Base version per the database design; extend here.

The regular tables are the source of truth; this is the history written alongside them, used
for throughput, metrics, and debugging. No foreign keys and only two secondary indexes keep
inserts cheap. Triggers in the migration reject UPDATE and DELETE. Reset between runs by
filtering on run_id, never by deleting.
"""
from datetime import datetime

from sqlalchemy import JSON, BigInteger, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigId, Timestamp3, utcnow


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("events_occurred_at_index", "occurred_at"),
        Index("events_event_type_occurred_at_index", "event_type", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    event_type: Mapped[str] = mapped_column(String(48))
    occurred_at: Mapped[datetime] = mapped_column(Timestamp3, default=utcnow)
    run_id: Mapped[int | None] = mapped_column(Integer)
    order_id: Mapped[int | None] = mapped_column(BigInteger)
    task_id: Mapped[int | None] = mapped_column(BigInteger)
    worker_id: Mapped[int | None] = mapped_column(Integer)
    assignment_id: Mapped[int | None] = mapped_column(BigInteger)
    payload: Mapped[dict | None] = mapped_column(JSON)

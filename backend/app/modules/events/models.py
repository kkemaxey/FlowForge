"""Append-only event log. One row per state change, written in the same transaction as the change."""
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, Timestamp, utcnow

# Every allowed event type. record_event() rejects anything else, which catches typos.
EVENT_TYPES = (
    "order_received",         # an order came in (Kanayo's intake)
    "task_created",           # a pick task was generated (Kanayo)
    "task_assigned",          # a task was given to a worker (Kanayo's assigner)
    "task_picked",            # a worker finished a pick (throughput counts these)
    "task_rerouted",          # a task moved to another bin after a stockout/jam
    "task_exception",         # a task couldn't be rerouted and waits for the supervisor
    "task_reopened",          # a task went back to "open" in place (worker_down)
    "order_completed",        # every task in an order was picked
    "exception_opened",       # a stockout/jam/worker_down was reported
    "worker_status_changed",  # a worker went idle/busy/down
)


class Event(Base):
    __tablename__ = "events"
    # Index on (run_id, type, created_at): makes the throughput query fast.
    __table_args__ = (Index("ix_events_run_type_created", "run_id", "type", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    # The simulation run this event belongs to.
    run_id: Mapped[int | None] = mapped_column(ForeignKey("sim_runs.id"))
    # One of EVENT_TYPES.
    type: Mapped[str] = mapped_column(String(32))
    # Entity ids are plain indexed columns, not foreign keys, so the log never blocks deletes elsewhere.
    # Each is filled in only if the event is about that kind of thing.
    order_id: Mapped[int | None] = mapped_column(Integer, index=True)
    task_id: Mapped[int | None] = mapped_column(Integer, index=True)
    worker_id: Mapped[int | None] = mapped_column(Integer)
    assignment_id: Mapped[int | None] = mapped_column(Integer)
    # Extra details as JSON, e.g. {"qty": 5, "location_id": 27} or {"from": "busy", "to": "idle"}.
    payload: Mapped[dict | None] = mapped_column(JSON)
    # When it happened (UTC, millisecond precision).
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)

"""Event log writes and metrics queries.

Other modules call record_event() inside their own transaction, right next to the
state change it describes, and commit both together.
"""
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.errors import ApiError
from app.modules.events.models import EVENT_TYPES, Event
from app.modules.simulation.models import SimRun


def active_run_id(db: Session) -> int | None:
    """The newest simulation run that hasn't ended, or None."""
    return db.scalar(
        # Runs with no ended_at are active; take the newest one.
        select(SimRun.id).where(SimRun.ended_at.is_(None)).order_by(SimRun.id.desc()).limit(1)
    )


def record_event(
    db: Session,
    type: str,
    # The * means everything after it must be passed by name, e.g. task_id=7.
    *,
    run_id: int | None = None,
    order_id: int | None = None,
    task_id: int | None = None,
    worker_id: int | None = None,
    assignment_id: int | None = None,
    payload: dict | None = None,
) -> Event:
    """Add an event to the caller's transaction (no commit). run_id defaults to the active run."""
    # Catch typos like "task_pickd" immediately instead of logging junk.
    if type not in EVENT_TYPES:
        raise ValueError(f"Unknown event type {type!r}")
    event = Event(
        type=type,
        # Use the run the caller gave us, otherwise whichever run is active.
        run_id=run_id if run_id is not None else active_run_id(db),
        order_id=order_id,
        task_id=task_id,
        worker_id=worker_id,
        assignment_id=assignment_id,
        payload=payload,
        created_at=utcnow(),
    )
    # Added to the session only. The caller's commit saves it along with the change it describes,
    # and the caller's rollback discards it, so the log never disagrees with the data.
    db.add(event)
    return event


def throughput(db: Session, run_id: int, window_minutes: int) -> tuple[int, datetime]:
    """task_picked events for the run in (as_of - window, as_of]. Returns (picks, as_of)."""
    if db.get(SimRun, run_id) is None:
        raise ApiError(404, f"Run {run_id} not found", "run_not_found")
    # "Now" — the end of the window.
    as_of = utcnow()
    picks = db.scalar(
        # SELECT COUNT(*) FROM events WHERE ...
        select(func.count())
        .select_from(Event)
        .where(
            Event.run_id == run_id,
            Event.type == "task_picked",
            # Only events from the last `window_minutes` minutes.
            Event.created_at > as_of - timedelta(minutes=window_minutes),
            Event.created_at <= as_of,
        )
    )
    return picks, as_of

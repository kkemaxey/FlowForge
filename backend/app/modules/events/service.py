"""Metrics worked out from the event log, for the live board."""
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.modules.events.models import Event
from app.modules.events.schemas import ActiveException, LiveMetrics, ThroughputBucket
from app.modules.simulation.models import TaskException
from app.modules.tasks.models import Task
from app.modules.warehouse.models import Location

# Hourly rates scale up what was picked in the last 5 minutes. The board labels the tile to match.
RATE_WINDOW = timedelta(minutes=5)


def live_metrics(session: Session) -> LiveMetrics:
    now = utcnow()
    picks = _picks_since(session, now - RATE_WINDOW)
    per_hour = timedelta(hours=1) / RATE_WINDOW
    return LiveMetrics(
        units_per_hour=round(sum(qty for _, qty in picks) * per_hour),
        tasks_per_hour=round(len(picks) * per_hour),
        active_exception=_newest_open_exception(session),
        as_of=now,
    )


def throughput(session: Session, minutes: int) -> list[ThroughputBucket]:
    """One bucket per minute, oldest first, ending with the current minute. Empty minutes count as 0."""
    current_minute = utcnow().replace(second=0, microsecond=0)
    starts = [current_minute - timedelta(minutes=ago) for ago in range(minutes - 1, -1, -1)]
    units = dict.fromkeys(starts, 0)
    tasks = dict.fromkeys(starts, 0)
    for occurred_at, qty in _picks_since(session, starts[0]):
        minute = occurred_at.replace(second=0, microsecond=0)
        if minute in units:
            units[minute] += qty
            tasks[minute] += 1
    return [ThroughputBucket(bucket_start=start, units=units[start], tasks=tasks[start]) for start in starts]


def _picks_since(session: Session, since: datetime) -> list[tuple[datetime, int]]:
    """(when, units) for each pick at or after since."""
    rows = session.execute(
        select(Event.occurred_at, Event.payload).where(Event.event_type == "task_picked", Event.occurred_at >= since)
    )
    return [(occurred_at, (payload or {}).get("qty", 0)) for occurred_at, payload in rows]


def _newest_open_exception(session: Session) -> ActiveException | None:
    row = session.execute(
        select(TaskException, Task.order_id, Location)
        .join(Task, Task.id == TaskException.task_id)
        .join(Location, Location.id == TaskException.from_location_id)
        .where(TaskException.resolved_at.is_(None))
        .order_by(TaskException.opened_at.desc(), TaskException.id.desc())
        .limit(1)
    ).first()
    if row is None:
        return None
    exception, order_id, location = row
    return ActiveException(
        task_id=exception.task_id,
        order_id=order_id,
        location=f"{location.aisle or location.zone or '?'} ({location.x},{location.y})",
        type=exception.type,
        raised_at=exception.opened_at,
    )

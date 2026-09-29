"""Turns the pick/exception event stream into throughput, WIP, and worker metrics."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Sequence

from typing_extensions import Protocol

from app.core.clock import utc_now
from app.core.exceptions import RuleViolationError
from app.modules.workforce.service import Worker, WorkerRepository

TASK_EVENT_TYPES = frozenset({"task_assigned", "task_picked", "task_exception"})
EVENT_TYPES = TASK_EVENT_TYPES | {"order_completed"}
MIN_WINDOW_MINUTES = 1
MAX_WINDOW_MINUTES = 1440


@dataclass(frozen=True)
class EventRecord:
    id: int
    ts: datetime
    type: str
    task_id: Optional[int]
    worker_id: Optional[int]
    qty: Optional[int]
    payload: Optional[Dict[str, Any]]


@dataclass(frozen=True)
class WorkerCounts:
    idle: int
    busy: int
    disabled: int


@dataclass(frozen=True)
class MetricsSnapshot:
    window_minutes: int
    units_picked: int
    throughput_per_hour: float
    wip: int
    exceptions: int
    workers: WorkerCounts


class EventRepository(Protocol):
    def add(self, event_type: str, ts: datetime, task_id: Optional[int], worker_id: Optional[int],
            qty: Optional[int], payload: Optional[Dict[str, Any]]) -> EventRecord: ...

    def list_since(self, cutoff: datetime) -> List[EventRecord]: ...

    def list_task_events(self) -> List[EventRecord]: ...


def units_picked(events: Sequence[EventRecord]) -> int:
    return sum(event.qty or 0 for event in events if event.type == "task_picked")


def throughput_per_hour(units: int, window_minutes: int) -> float:
    return round(units * 60 / window_minutes, 1)


def count_exceptions(events: Sequence[EventRecord]) -> int:
    return sum(1 for event in events if event.type == "task_exception")


def work_in_progress(task_events: Sequence[EventRecord]) -> int:
    """Tasks whose most recent event is an assignment. Events must be in chronological order."""
    latest_type_by_task: Dict[int, str] = {}
    for event in task_events:
        if event.type in TASK_EVENT_TYPES and event.task_id is not None:
            latest_type_by_task[event.task_id] = event.type
    return sum(1 for event_type in latest_type_by_task.values() if event_type == "task_assigned")


def count_workers(workers: Sequence[Worker]) -> WorkerCounts:
    enabled = [worker for worker in workers if worker.enabled]
    return WorkerCounts(
        idle=sum(1 for worker in enabled if worker.status == "idle"),
        busy=sum(1 for worker in enabled if worker.status == "busy"),
        disabled=len(workers) - len(enabled),
    )


class MetricsService:
    def __init__(self, events: EventRepository, workers: WorkerRepository,
                 clock: Callable[[], datetime] = utc_now):
        self._events = events
        self._workers = workers
        self._clock = clock

    def record_event(self, event_type: str, task_id: Optional[int] = None,
                     worker_id: Optional[int] = None, qty: Optional[int] = None,
                     payload: Optional[Dict[str, Any]] = None) -> EventRecord:
        if event_type not in EVENT_TYPES:
            raise RuleViolationError(
                "unknown_event_type",
                f"Event type must be one of: {', '.join(sorted(EVENT_TYPES))}",
            )
        if event_type in TASK_EVENT_TYPES and task_id is None:
            raise RuleViolationError("task_id_required", f"'{event_type}' events need a task_id")
        if event_type == "task_picked" and (qty is None or qty < 1):
            raise RuleViolationError("qty_required", "'task_picked' events need a qty of at least 1")

        return self._events.add(event_type, self._clock(), task_id, worker_id, qty, payload)

    def snapshot(self, window_minutes: int) -> MetricsSnapshot:
        if not MIN_WINDOW_MINUTES <= window_minutes <= MAX_WINDOW_MINUTES:
            raise RuleViolationError(
                "invalid_window",
                f"window_minutes must be between {MIN_WINDOW_MINUTES} and {MAX_WINDOW_MINUTES}",
            )

        cutoff = self._clock() - timedelta(minutes=window_minutes)
        window_events = self._events.list_since(cutoff)
        units = units_picked(window_events)

        return MetricsSnapshot(
            window_minutes=window_minutes,
            units_picked=units,
            throughput_per_hour=throughput_per_hour(units, window_minutes),
            wip=work_in_progress(self._events.list_task_events()),
            exceptions=count_exceptions(window_events),
            workers=count_workers(self._workers.list_workers()),
        )

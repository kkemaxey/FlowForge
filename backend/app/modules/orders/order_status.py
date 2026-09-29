"""Order status from the course data model: new | in_progress | complete | late."""
from collections.abc import Iterable
from datetime import datetime
from enum import StrEnum

from app.modules.orders.task_states import TaskStatus


class OrderStatus(StrEnum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    LATE = "late"


class OrderPriority(StrEnum):
    NORMAL = "normal"
    EXPEDITE = "expedite"


def progress_status(task_statuses: Iterable[str]) -> OrderStatus:
    """Where the order's work stands, ignoring the clock."""
    statuses = list(task_statuses)
    if statuses and all(status == TaskStatus.PICKED for status in statuses):
        return OrderStatus.COMPLETE
    if all(status == TaskStatus.OPEN for status in statuses):
        return OrderStatus.NEW
    return OrderStatus.IN_PROGRESS


def effective_status(stored_status: str, due_at: datetime, now: datetime) -> OrderStatus:
    """An unfinished order past its due time is late, whatever its progress."""
    status = OrderStatus(stored_status)
    if status != OrderStatus.COMPLETE and due_at < now:
        return OrderStatus.LATE
    return status

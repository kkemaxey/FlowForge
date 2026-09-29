"""Pick-task lifecycle from the course data model: open | assigned | picked | exception.

    open ──► assigned ──► picked
      ▲         │
      ├─────────┘ (unassign / reassign)
      │         ▼
      └──── exception   (stockout or jam while a worker holds the task)
"""
from enum import StrEnum

from app.core.errors import InvalidTransitionError


class TaskStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    PICKED = "picked"
    EXCEPTION = "exception"


ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.OPEN: {TaskStatus.ASSIGNED},
    TaskStatus.ASSIGNED: {TaskStatus.PICKED, TaskStatus.EXCEPTION, TaskStatus.OPEN},
    TaskStatus.EXCEPTION: {TaskStatus.OPEN},
    TaskStatus.PICKED: set(),
}

# Tasks a worker is currently holding count as work-in-progress.
WIP_STATUSES = {TaskStatus.ASSIGNED}


def can_transition(current: TaskStatus, target: TaskStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def ensure_transition(current: TaskStatus, target: TaskStatus) -> None:
    if not can_transition(current, target):
        raise InvalidTransitionError(
            f"Cannot move a task from '{current}' to '{target}'."
        )

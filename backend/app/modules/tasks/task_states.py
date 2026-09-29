"""Pick-task lifecycle: which status changes are allowed.

    open ──► assigned ──► in_progress ──► picked
      ▲         │               │
      └─────────┘ (unassign)    │
      ▲                         ▼
      └──────── exception ◄─────┘   (any active status can raise an exception)
"""
from enum import StrEnum

from app.core.errors import InvalidTransitionError


class TaskStatus(StrEnum):
    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    PICKED = "picked"
    EXCEPTION = "exception"


class TaskPriority(StrEnum):
    NORMAL = "normal"
    EXPEDITE = "expedite"


ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.OPEN: {TaskStatus.ASSIGNED, TaskStatus.EXCEPTION},
    TaskStatus.ASSIGNED: {TaskStatus.IN_PROGRESS, TaskStatus.OPEN, TaskStatus.EXCEPTION},
    TaskStatus.IN_PROGRESS: {TaskStatus.PICKED, TaskStatus.EXCEPTION},
    TaskStatus.EXCEPTION: {TaskStatus.OPEN},
    TaskStatus.PICKED: set(),
}

# Statuses that count as work-in-progress on the live board.
WIP_STATUSES = {TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS}
# Statuses where a task still has to be finished, so it can run late.
ACTIVE_STATUSES = {TaskStatus.OPEN, TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS,
                   TaskStatus.EXCEPTION}


def can_transition(current: TaskStatus, target: TaskStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def ensure_transition(current: TaskStatus, target: TaskStatus) -> None:
    if not can_transition(current, target):
        raise InvalidTransitionError(
            f"Cannot move a task from '{current}' to '{target}'."
        )

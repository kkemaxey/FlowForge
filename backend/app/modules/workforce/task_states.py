"""Pick-task lifecycle: open -> assigned -> picked, with exception and reassignment paths."""
from enum import Enum
from typing import Dict, FrozenSet

from app.core.exceptions import InvalidTransitionError


class TaskStatus(str, Enum):
    OPEN = "open"
    ASSIGNED = "assigned"
    PICKED = "picked"
    EXCEPTION = "exception"


ALLOWED_TRANSITIONS: Dict[TaskStatus, FrozenSet[TaskStatus]] = {
    TaskStatus.OPEN: frozenset({TaskStatus.ASSIGNED}),
    TaskStatus.ASSIGNED: frozenset({TaskStatus.PICKED, TaskStatus.EXCEPTION, TaskStatus.OPEN}),
    TaskStatus.EXCEPTION: frozenset({TaskStatus.OPEN}),
    TaskStatus.PICKED: frozenset(),
}


def can_transition(current: TaskStatus, target: TaskStatus) -> bool:
    return target in ALLOWED_TRANSITIONS[current]


def transition(current: TaskStatus, target: TaskStatus) -> TaskStatus:
    if not can_transition(current, target):
        raise InvalidTransitionError(
            "invalid_task_transition",
            f"Cannot move a task from '{current.value}' to '{target.value}'",
        )
    return target

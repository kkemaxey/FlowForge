import pytest

from app.core.errors import InvalidTransitionError
from app.modules.tasks.task_states import (ALLOWED_TRANSITIONS, TaskStatus, can_transition,
                                           ensure_transition)


@pytest.mark.parametrize("current, target", [
    (TaskStatus.OPEN, TaskStatus.ASSIGNED),
    (TaskStatus.ASSIGNED, TaskStatus.IN_PROGRESS),
    (TaskStatus.IN_PROGRESS, TaskStatus.PICKED),
    (TaskStatus.ASSIGNED, TaskStatus.OPEN),
    (TaskStatus.IN_PROGRESS, TaskStatus.EXCEPTION),
    (TaskStatus.EXCEPTION, TaskStatus.OPEN),
])
def test_allowed_transitions(current, target):
    assert can_transition(current, target)
    ensure_transition(current, target)  # does not raise


@pytest.mark.parametrize("current, target", [
    (TaskStatus.OPEN, TaskStatus.PICKED),
    (TaskStatus.OPEN, TaskStatus.IN_PROGRESS),
    (TaskStatus.EXCEPTION, TaskStatus.PICKED),
    (TaskStatus.PICKED, TaskStatus.OPEN),
])
def test_disallowed_transitions_raise(current, target):
    assert not can_transition(current, target)
    with pytest.raises(InvalidTransitionError):
        ensure_transition(current, target)


def test_picked_is_terminal():
    assert ALLOWED_TRANSITIONS[TaskStatus.PICKED] == set()


def test_every_status_has_a_transition_rule():
    assert set(ALLOWED_TRANSITIONS) == set(TaskStatus)

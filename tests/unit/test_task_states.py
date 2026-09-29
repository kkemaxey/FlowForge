import pytest

from app.services.errors import ConflictError, InvalidTransitionError
from app.services.task_states import TaskStatus, can_transition, transition

LEGAL_TRANSITIONS = [
    (TaskStatus.OPEN, TaskStatus.ASSIGNED),
    (TaskStatus.ASSIGNED, TaskStatus.PICKED),
    (TaskStatus.ASSIGNED, TaskStatus.EXCEPTION),
    (TaskStatus.ASSIGNED, TaskStatus.OPEN),
    (TaskStatus.EXCEPTION, TaskStatus.OPEN),
]

ILLEGAL_TRANSITIONS = [
    (TaskStatus.OPEN, TaskStatus.PICKED),
    (TaskStatus.OPEN, TaskStatus.EXCEPTION),
    (TaskStatus.OPEN, TaskStatus.OPEN),
    (TaskStatus.ASSIGNED, TaskStatus.ASSIGNED),
    (TaskStatus.EXCEPTION, TaskStatus.PICKED),
    (TaskStatus.EXCEPTION, TaskStatus.ASSIGNED),
    (TaskStatus.PICKED, TaskStatus.OPEN),
    (TaskStatus.PICKED, TaskStatus.ASSIGNED),
    (TaskStatus.PICKED, TaskStatus.EXCEPTION),
]


@pytest.mark.parametrize("current, target", LEGAL_TRANSITIONS)
def test_legal_transition_returns_target(current, target):
    assert can_transition(current, target) is True
    assert transition(current, target) is target


@pytest.mark.parametrize("current, target", ILLEGAL_TRANSITIONS)
def test_illegal_transition_raises(current, target):
    assert can_transition(current, target) is False
    with pytest.raises(InvalidTransitionError) as error:
        transition(current, target)
    assert error.value.code == "invalid_task_transition"
    assert current.value in error.value.message
    assert target.value in error.value.message


def test_picked_is_terminal():
    assert not any(can_transition(TaskStatus.PICKED, target) for target in TaskStatus)


def test_invalid_transition_is_a_conflict():
    assert issubclass(InvalidTransitionError, ConflictError)

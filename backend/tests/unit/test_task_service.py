from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.core.errors import InvalidTransitionError, NotFoundError, ValidationFailedError
from app.modules.tasks.schema import TaskCreate, TaskStatusUpdate
from app.modules.tasks.service import TaskService
from app.modules.tasks.task_states import TaskPriority, TaskStatus
from tests.unit.fakes import FakeTaskRepository, FixedClock

NOW = datetime(2026, 10, 1, 14, 0, 0)


@pytest.fixture
def clock():
    return FixedClock(NOW)


@pytest.fixture
def repository():
    return FakeTaskRepository()


@pytest.fixture
def service(repository, clock):
    return TaskService(repository, clock=clock)


def new_task_request(**overrides) -> TaskCreate:
    fields = {"order_ref": "ORD-100", "sku": "sku-1", "bin_location": "b-07-3",
              "quantity": 2, "due_at": NOW + timedelta(minutes=45)}
    fields.update(overrides)
    return TaskCreate(**fields)


def test_create_task_starts_open_and_normalizes_fields(service):
    task = service.create_task(new_task_request())
    assert task.id == 1
    assert task.status == TaskStatus.OPEN
    assert task.sku == "SKU-1"
    assert task.bin_location == "B-07-3"
    assert task.priority == TaskPriority.NORMAL
    assert task.created_at == NOW


def test_create_task_converts_aware_due_time_to_utc(service):
    eastern = timezone(timedelta(hours=-4))
    due_local = datetime(2026, 10, 1, 11, 0, tzinfo=eastern)  # 15:00 UTC
    task = service.create_task(new_task_request(due_at=due_local))
    assert task.due_at == datetime(2026, 10, 1, 15, 0)


def test_create_task_rejects_due_time_in_the_past(service):
    with pytest.raises(ValidationFailedError):
        service.create_task(new_task_request(due_at=NOW - timedelta(minutes=1)))


def test_get_missing_task_raises_not_found(service):
    with pytest.raises(NotFoundError):
        service.get_task(99)


def test_full_happy_path_records_worker_and_completion(service, clock):
    task = service.create_task(new_task_request())
    service.change_status(task.id, TaskStatusUpdate(status="assigned", worker_id=7))
    assert task.assigned_worker_id == 7

    service.change_status(task.id, TaskStatusUpdate(status="in_progress"))
    clock.now = NOW + timedelta(minutes=10)
    service.change_status(task.id, TaskStatusUpdate(status="picked"))

    assert task.status == TaskStatus.PICKED
    assert task.completed_at == NOW + timedelta(minutes=10)
    assert task.updated_at == NOW + timedelta(minutes=10)


def test_assigning_without_worker_is_rejected(service):
    task = service.create_task(new_task_request())
    with pytest.raises(ValidationFailedError):
        service.change_status(task.id, TaskStatusUpdate(status="assigned"))
    assert task.status == TaskStatus.OPEN


def test_exception_requires_reason(service):
    task = service.create_task(new_task_request())
    with pytest.raises(ValidationFailedError):
        service.change_status(task.id, TaskStatusUpdate(status="exception", reason="  "))


def test_exception_then_reopen_clears_worker_and_reason(service):
    task = service.create_task(new_task_request())
    service.change_status(task.id, TaskStatusUpdate(status="assigned", worker_id=3))
    service.change_status(task.id, TaskStatusUpdate(status="exception", reason="Bin empty"))
    assert task.exception_reason == "Bin empty"

    service.change_status(task.id, TaskStatusUpdate(status="open"))
    assert task.assigned_worker_id is None
    assert task.exception_reason is None


def test_skipping_a_step_is_rejected(service):
    task = service.create_task(new_task_request())
    with pytest.raises(InvalidTransitionError):
        service.change_status(task.id, TaskStatusUpdate(status="picked"))


def test_expedite_raises_priority(service):
    task = service.create_task(new_task_request())
    service.expedite(task.id)
    assert task.priority == TaskPriority.EXPEDITE


def test_cannot_expedite_picked_task(service):
    task = service.create_task(new_task_request())
    for step in (TaskStatusUpdate(status="assigned", worker_id=1),
                 TaskStatusUpdate(status="in_progress"),
                 TaskStatusUpdate(status="picked")):
        service.change_status(task.id, step)
    with pytest.raises(ValidationFailedError):
        service.expedite(task.id)


def test_list_tasks_filters_by_status(service):
    first = service.create_task(new_task_request(order_ref="A"))
    service.create_task(new_task_request(order_ref="B"))
    service.change_status(first.id, TaskStatusUpdate(status="assigned", worker_id=2))

    assigned = service.list_tasks(TaskStatus.ASSIGNED)
    assert [t.order_ref for t in assigned] == ["A"]
    assert len(service.list_tasks()) == 2


def test_live_board_uses_the_service_clock(service, clock):
    service.create_task(new_task_request(due_at=NOW + timedelta(minutes=5)))
    clock.now = NOW + timedelta(minutes=20)
    board = service.live_board()
    assert board.generated_at == clock.now
    assert board.summary.late_tasks == 1


def test_default_clock_is_naive_utc():
    service = TaskService(FakeTaskRepository())
    task = service.create_task(new_task_request(
        due_at=datetime.now(UTC) + timedelta(hours=1)))
    assert task.created_at.tzinfo is None


def test_stored_times_drop_fractional_seconds(service):
    task = service.create_task(new_task_request(
        due_at=NOW + timedelta(minutes=30, microseconds=844316)))
    assert task.due_at == NOW + timedelta(minutes=30)

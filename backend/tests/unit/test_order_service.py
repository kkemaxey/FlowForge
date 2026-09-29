from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.core.errors import InvalidTransitionError, NotFoundError, ValidationFailedError
from app.modules.orders.order_status import OrderPriority, OrderStatus
from app.modules.orders.schema import OrderCreate, TaskStatusUpdate
from app.modules.orders.service import OrderService
from app.modules.orders.task_states import TaskStatus
from tests.unit.fakes import FakeOrderRepository, FixedClock

NOW = datetime(2026, 10, 1, 14, 0, 0)


@pytest.fixture
def clock():
    return FixedClock(NOW)


@pytest.fixture
def repository():
    return FakeOrderRepository()


@pytest.fixture
def service(repository, clock):
    return OrderService(repository, clock=clock)


def order_request(line_count=1, **overrides) -> OrderCreate:
    fields = {
        "due_at": NOW + timedelta(minutes=45),
        "lines": [{"sku_id": f"sku-{n}", "qty": n + 1, "location_id": f"a1-0{n + 1}"}
                  for n in range(line_count)],
    }
    fields.update(overrides)
    return OrderCreate(**fields)


def assign(service, task_id, worker_id=7):
    return service.change_task_status(task_id,
                                      TaskStatusUpdate(status="assigned", worker_id=worker_id))


def test_create_order_generates_one_open_task_per_line(service):
    order = service.create_order(order_request(line_count=3))
    assert order.status == OrderStatus.NEW
    assert [task.status for task in order.tasks] == [TaskStatus.OPEN] * 3
    assert [task.location_id for task in order.tasks] == ["A1-01", "A1-02", "A1-03"]
    assert order.tasks[0].sku_id == "SKU-0"
    assert all(task.order_id == order.id for task in order.tasks)


def test_create_order_converts_aware_due_time_to_utc(service):
    eastern = timezone(timedelta(hours=-4))
    order = service.create_order(order_request(
        due_at=datetime(2026, 10, 1, 11, 0, tzinfo=eastern)))  # 15:00 UTC
    assert order.due_at == datetime(2026, 10, 1, 15, 0)


def test_stored_times_drop_fractional_seconds(service):
    order = service.create_order(order_request(
        due_at=NOW + timedelta(minutes=30, microseconds=844316)))
    assert order.due_at == NOW + timedelta(minutes=30)


def test_create_order_rejects_due_time_in_the_past(service):
    with pytest.raises(ValidationFailedError):
        service.create_order(order_request(due_at=NOW - timedelta(minutes=1)))


def test_missing_order_and_task_raise_not_found(service):
    with pytest.raises(NotFoundError):
        service.get_order(99)
    with pytest.raises(NotFoundError):
        service.get_task(99)


def test_assign_then_pick_records_the_assignment(service, clock):
    task_id = service.create_order(order_request()).tasks[0].id
    assigned = assign(service, task_id, worker_id=7)
    assert assigned.worker_id == 7
    assert assigned.assigned_at == NOW

    clock.now = NOW + timedelta(minutes=10)
    picked = service.change_task_status(task_id, TaskStatusUpdate(status="picked"))
    assert picked.status == TaskStatus.PICKED
    assert picked.completed_at == NOW + timedelta(minutes=10)


def test_order_status_follows_its_tasks(service):
    order = service.create_order(order_request(line_count=2))
    first, second = (task.id for task in order.tasks)

    assign(service, first)
    assert service.get_order(order.id).status == OrderStatus.IN_PROGRESS

    for task_id in (first, second):
        if task_id == second:
            assign(service, task_id)
        service.change_task_status(task_id, TaskStatusUpdate(status="picked"))
    assert service.get_order(order.id).status == OrderStatus.COMPLETE


def test_unfinished_order_reads_late_after_due_time(service, clock):
    order = service.create_order(order_request())
    clock.now = NOW + timedelta(hours=1)
    assert service.get_order(order.id).status == OrderStatus.LATE


def test_assigning_without_worker_is_rejected(service):
    task_id = service.create_order(order_request()).tasks[0].id
    with pytest.raises(ValidationFailedError):
        service.change_task_status(task_id, TaskStatusUpdate(status="assigned"))
    assert service.get_task(task_id).status == TaskStatus.OPEN


def test_exception_then_reopen_frees_the_task_for_reassignment(service):
    task_id = service.create_order(order_request()).tasks[0].id
    assign(service, task_id, worker_id=3)
    service.change_task_status(task_id, TaskStatusUpdate(status="exception"))
    assert service.get_task(task_id).worker_id == 3

    reopened = service.change_task_status(task_id, TaskStatusUpdate(status="open"))
    assert reopened.worker_id is None
    assert assign(service, task_id, worker_id=9).worker_id == 9


def test_skipping_a_step_is_rejected(service):
    task_id = service.create_order(order_request()).tasks[0].id
    with pytest.raises(InvalidTransitionError):
        service.change_task_status(task_id, TaskStatusUpdate(status="picked"))


def test_expedite_raises_order_priority(service):
    order = service.create_order(order_request())
    assert service.expedite_order(order.id).priority == OrderPriority.EXPEDITE


def test_cannot_expedite_complete_order(service):
    order = service.create_order(order_request())
    task_id = order.tasks[0].id
    assign(service, task_id)
    service.change_task_status(task_id, TaskStatusUpdate(status="picked"))
    with pytest.raises(ValidationFailedError):
        service.expedite_order(order.id)


def test_list_tasks_filters_by_status(service):
    first = service.create_order(order_request()).tasks[0].id
    service.create_order(order_request())
    assign(service, first)
    assert [task.id for task in service.list_tasks(TaskStatus.ASSIGNED)] == [first]
    assert len(service.list_tasks()) == 2


def test_live_board_uses_the_service_clock(service, clock):
    service.create_order(order_request(due_at=NOW + timedelta(minutes=5)))
    clock.now = NOW + timedelta(minutes=20)
    board = service.live_board()
    assert board.generated_at == clock.now
    assert board.summary.late_orders == 1


def test_default_clock_is_naive_utc():
    service = OrderService(FakeOrderRepository())
    order = service.create_order(order_request(due_at=datetime.now(UTC) + timedelta(hours=1)))
    assert order.created_at.tzinfo is None

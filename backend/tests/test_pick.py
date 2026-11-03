"""POST /api/v1/tasks/{task_id}/pick against the MySQL test database."""
import re
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.assignment.models import Assignment, AssignmentOutcome
from app.modules.events.models import Event
from app.modules.orders.models import Order, OrderStatus
from app.modules.tasks.models import Task, TaskStatus
from app.modules.warehouse.models import Inventory
from app.modules.workforce.models import Worker, WorkerStatus

ISO_MS_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def pick(client, task_id, assignment_id):
    return client.post(f"/api/v1/tasks/{task_id}/pick", json={"assignment_id": assignment_id})


def fresh(model, *key):
    with SessionLocal() as session:
        return session.get(model, key if len(key) > 1 else key[0])


def event_types():
    with SessionLocal() as session:
        return list(session.scalars(select(Event.event_type).order_by(Event.id)))


def stock_of(task):
    return fresh(Inventory, task.location_id, task.sku_id)


@pytest.fixture
def holding(db, floor):
    """Give a task a busy worker, an open assignment, and a bin holding on_hand with its qty reserved."""

    def make(x=4, y=5, qty=2, on_hand=10, reserved=None, order=None, status=TaskStatus.assigned):
        task = floor.task(x, y, status=status, order=order)
        task.qty = qty
        db.add(Inventory(
            location_id=task.location_id, sku_id=task.sku_id, qty_on_hand=on_hand,
            qty_reserved=qty if reserved is None else reserved,
        ))
        db.commit()
        worker = floor.worker(x + 100, y, status=WorkerStatus.busy)
        return task, worker, floor.assign(task, worker)

    return make


def assert_error(response, status_code, code):
    assert response.status_code == status_code, response.text
    assert response.json()["code"] == code


def test_pick_last_task_completes_the_order(client, floor, holding):
    task, worker, assignment = holding(x=4, y=5, qty=2, on_hand=10)
    version = task.version

    response = pick(client, task.id, assignment.id)

    assert response.status_code == 200, response.text
    body = response.json()
    assert ISO_MS_Z.match(body.pop("picked_at"))
    assert body == {
        "task_id": task.id,
        "status": "picked",
        "version": version + 1,
        "assignment_id": assignment.id,
        "worker_id": worker.id,
        "order_id": floor.order_id,
        "order_status": "complete",
    }
    stored_task = fresh(Task, task.id)
    assert (stored_task.status, stored_task.version) == (TaskStatus.picked, version + 1)
    stored_assignment = fresh(Assignment, assignment.id)
    assert stored_assignment.ended_at is not None
    assert stored_assignment.outcome is AssignmentOutcome.completed
    stock = stock_of(task)
    assert (stock.qty_on_hand, stock.qty_reserved) == (8, 0)
    stored_worker = fresh(Worker, worker.id)
    assert (stored_worker.status, stored_worker.x, stored_worker.y) == (WorkerStatus.idle, 4, 5)
    order = fresh(Order, floor.order_id)
    assert order.status is OrderStatus.complete
    assert order.completed_at is not None
    assert order.version == 1
    assert event_types() == ["task_picked", "worker_status_changed", "order_completed"]


def test_order_stays_open_until_its_last_task_is_picked(client, floor, holding):
    first, _, first_assignment = holding(x=1, y=1)
    second, _, second_assignment = holding(x=2, y=2)

    assert pick(client, first.id, first_assignment.id).json()["order_status"] == "open"
    order = fresh(Order, floor.order_id)
    assert (order.status, order.completed_at) == (OrderStatus.open, None)
    assert "order_completed" not in event_types()

    assert pick(client, second.id, second_assignment.id).json()["order_status"] == "complete"
    assert event_types().count("order_completed") == 1


@pytest.mark.parametrize("other_status", [TaskStatus.open, TaskStatus.exception])
def test_unfinished_tasks_keep_the_order_open(client, floor, holding, other_status):
    task, _, assignment = holding()
    floor.task(9, 9, status=other_status)

    assert pick(client, task.id, assignment.id).json()["order_status"] == "open"


def test_picking_twice_is_409_and_changes_nothing_more(client, holding):
    task, _, assignment = holding(qty=2, on_hand=10)
    pick(client, task.id, assignment.id)

    assert_error(pick(client, task.id, assignment.id), 409, "assignment_not_active")

    assert stock_of(task).qty_on_hand == 8
    assert event_types().count("task_picked") == 1


def test_an_assignment_that_was_reassigned_cannot_pick(client, db, floor, holding):
    task, worker, assignment = holding()
    assignment.ended_at = assignment.assigned_at
    assignment.outcome = AssignmentOutcome.reassigned
    db.commit()

    assert_error(pick(client, task.id, assignment.id), 409, "assignment_not_active")

    assert fresh(Task, task.id).status is TaskStatus.assigned
    assert fresh(Worker, worker.id).status is WorkerStatus.busy


def test_a_task_that_is_not_assigned_cannot_be_picked(client, holding):
    task, _, assignment = holding(status=TaskStatus.exception)

    assert_error(pick(client, task.id, assignment.id), 409, "invalid_transition")

    assert fresh(Assignment, assignment.id).ended_at is None


@pytest.mark.parametrize("on_hand, has_row", [(1, True), (0, False)])
def test_short_bin_is_409_and_nothing_changes(client, db, holding, on_hand, has_row):
    task, worker, assignment = holding(qty=2, on_hand=on_hand, reserved=0)
    if not has_row:
        db.delete(db.get(Inventory, (task.location_id, task.sku_id)))
        db.commit()
    version = fresh(Task, task.id).version

    assert_error(pick(client, task.id, assignment.id), 409, "insufficient_stock")

    stored = fresh(Task, task.id)
    assert (stored.status, stored.version) == (TaskStatus.assigned, version)
    assert fresh(Assignment, assignment.id).ended_at is None
    assert fresh(Worker, worker.id).status is WorkerStatus.busy
    assert event_types() == []


def test_exact_stock_empties_the_bin(client, holding):
    task, _, assignment = holding(qty=3, on_hand=3)

    assert pick(client, task.id, assignment.id).status_code == 200

    stock = stock_of(task)
    assert (stock.qty_on_hand, stock.qty_reserved) == (0, 0)


def test_reservation_smaller_than_the_task_stops_at_zero(client, holding):
    task, _, assignment = holding(qty=3, on_hand=10, reserved=1)

    assert pick(client, task.id, assignment.id).status_code == 200

    stock = stock_of(task)
    assert (stock.qty_on_hand, stock.qty_reserved) == (7, 0)


def test_other_reservations_in_the_bin_are_kept(client, holding):
    task, _, assignment = holding(qty=2, on_hand=10, reserved=5)

    pick(client, task.id, assignment.id)

    assert stock_of(task).qty_reserved == 3


def test_worker_marked_down_stays_down_but_moves(client, db, holding):
    task, worker, assignment = holding(x=4, y=5)
    worker.status = WorkerStatus.down
    db.commit()

    assert pick(client, task.id, assignment.id).status_code == 200

    stored = fresh(Worker, worker.id)
    assert (stored.status, stored.x, stored.y) == (WorkerStatus.down, 4, 5)
    assert "worker_status_changed" not in event_types()


def test_pick_does_not_bump_the_worker_version(client, holding):
    task, worker, assignment = holding()
    version = fresh(Worker, worker.id).version

    pick(client, task.id, assignment.id)

    assert fresh(Worker, worker.id).version == version


def test_freed_worker_and_completed_order_show_in_the_api(client, floor, holding):
    task, worker, assignment = holding()

    pick(client, task.id, assignment.id)

    order = client.get(f"/api/v1/orders/{floor.order_id}").json()
    assert order["status"] == "complete"
    assert ISO_MS_Z.match(order["completed_at"])
    assert client.get(f"/api/v1/workers/{worker.id}").json()["status"] == "idle"


def test_unknown_task_or_assignment_is_404(client, holding):
    task, _, assignment = holding()

    assert_error(pick(client, 999_999, assignment.id), 404, "task_not_found")
    assert_error(pick(client, task.id, 999_999), 404, "assignment_not_found")


def test_assignment_for_another_task_is_422(client, holding):
    task, _, _ = holding(x=1, y=1)
    _, _, other_assignment = holding(x=2, y=2)

    assert_error(pick(client, task.id, other_assignment.id), 422, "assignment_mismatch")


@pytest.mark.parametrize("body", [{}, {"assignment_id": 0}, {"assignment_id": 1, "extra": 1}])
def test_bad_body_is_422(client, holding, body):
    task, _, _ = holding()

    response = client.post(f"/api/v1/tasks/{task.id}/pick", json=body)

    assert_error(response, 422, "validation_error")


@pytest.mark.parametrize("round_", range(5))
def test_simultaneous_last_picks_complete_the_order(client, floor, holding, round_):
    order = floor.order()
    picks = [holding(x=1, y=1, order=order), holding(x=2, y=2, order=order), holding(x=3, y=3, order=order)]
    start = Barrier(len(picks))

    def run(held):
        task, _, assignment = held
        start.wait()
        return pick(client, task.id, assignment.id)

    with ThreadPoolExecutor(len(picks)) as pool:
        responses = list(pool.map(run, picks))

    assert [r.status_code for r in responses] == [200, 200, 200]
    stored = fresh(Order, order.id)
    assert stored.status is OrderStatus.complete
    assert stored.completed_at is not None
    assert event_types().count("order_completed") == 1

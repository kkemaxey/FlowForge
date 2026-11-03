"""Exceptions, rerouting and worker recovery against the MySQL test database."""
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from threading import Barrier

import pytest
from sqlalchemy import func, select

from app.core.database import SessionLocal, utcnow
from app.modules.assignment import service as assigner
from app.modules.assignment.models import Assignment, AssignmentOutcome
from app.modules.events.models import Event
from app.modules.orders.models import Order, OrderStatus
from app.modules.simulation import service
from app.modules.simulation.models import ExceptionType, TaskException
from app.modules.tasks.models import Task, TaskStatus
from app.modules.warehouse.models import Inventory, Location, LocationKind
from app.modules.workforce.models import Worker, WorkerStatus

ISO_MS_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")
LIST_URL = "/api/v1/exceptions"


@dataclass
class World:
    task: Task
    worker: Worker
    assignment: Assignment
    bin_a: int
    near: int
    far: int


def fresh(model, *key):
    with SessionLocal() as session:
        return session.get(model, key if len(key) > 1 else key[0])


def event_types():
    with SessionLocal() as session:
        return list(session.scalars(select(Event.event_type).order_by(Event.id)))


def exception_count():
    with SessionLocal() as session:
        return session.scalar(select(func.count()).select_from(TaskException))


def stock(world, location_id):
    row = fresh(Inventory, location_id, world.task.sku_id)
    return row.qty_on_hand, row.qty_reserved


def report(client, world, **body):
    payload = {"assignment_id": world.assignment.id, **body}
    return client.post(f"/api/v1/tasks/{world.task.id}/exceptions", json=payload)


@pytest.fixture
def build(db, floor):
    """A busy worker picking qty 4 from bin A, with the same shoe in a nearer and a farther bin."""

    def make(near_stock=20, far_stock=50, near_reserved=0, qty=4):
        task = floor.task(0, 2, status=TaskStatus.assigned)
        task.qty = qty
        near = Location(x=2, y=5, kind=LocationKind.storage)
        far = Location(x=17, y=20, kind=LocationKind.storage)
        db.add_all([near, far])
        db.flush()
        db.add_all([
            Inventory(location_id=task.location_id, sku_id=task.sku_id, qty_on_hand=10, qty_reserved=qty),
            Inventory(location_id=near.id, sku_id=task.sku_id, qty_on_hand=near_stock, qty_reserved=near_reserved),
            Inventory(location_id=far.id, sku_id=task.sku_id, qty_on_hand=far_stock),
        ])
        db.commit()
        worker = floor.worker(1, 1, status=WorkerStatus.busy)
        assignment = floor.assign(task, worker)
        return World(task, worker, assignment, task.location_id, near.id, far.id)

    return make


def assert_error(response, status_code, code):
    assert response.status_code == status_code, response.text
    assert response.json()["code"] == code


# --- stockout and jam: moving the task ------------------------------------------------------------


def test_stockout_reroutes_to_the_nearest_bin_with_stock(client, floor, build):
    world = build()
    version = world.task.version

    response = report(client, world, type="stockout", qty_found=1)

    assert response.status_code == 201, response.text
    body = response.json()
    assert ISO_MS_Z.match(body.pop("opened_at"))
    exception_id = body.pop("exception_id")
    assert body == {
        "type": "stockout", "task_id": world.task.id, "task_status": "open", "rerouted_to_location_id": world.near,
    }
    task = fresh(Task, world.task.id)
    assert (task.status, task.location_id, task.version) == (TaskStatus.open, world.near, version + 1)
    assignment = fresh(Assignment, world.assignment.id)
    assert assignment.outcome is AssignmentOutcome.failed
    assert assignment.ended_at is not None
    assert fresh(Worker, world.worker.id).status is WorkerStatus.idle
    assert stock(world, world.bin_a) == (1, 0)
    assert stock(world, world.near) == (20, 4)
    assert stock(world, world.far) == (50, 0)
    stored = fresh(TaskException, exception_id)
    assert (stored.from_location_id, stored.qty_found, stored.run_id) == (world.bin_a, 1, floor.run_id)
    assert stored.resolved_at == stored.opened_at
    assert event_types() == ["exception_opened", "worker_status_changed", "task_rerouted"]


def test_jam_releases_the_reservation_and_leaves_stock_alone(client, build):
    world = build()

    body = report(client, world, type="jam").json()

    assert body["rerouted_to_location_id"] == world.near
    assert stock(world, world.bin_a) == (10, 0)


def test_reroute_skips_bins_without_enough_unreserved_stock(client, build):
    world = build(near_stock=10, near_reserved=7)

    body = report(client, world, type="jam").json()

    assert body["rerouted_to_location_id"] == world.far
    assert stock(world, world.far) == (50, 4)
    assert stock(world, world.near) == (10, 7)


def test_bin_with_more_reserved_than_on_hand_does_not_break_the_reroute(client, build):
    # A stockout leaves a bin like this. MySQL errors if it subtracts these unsigned columns.
    world = build(near_stock=2, near_reserved=5)

    response = report(client, world, type="jam")

    assert response.status_code == 201, response.text
    assert response.json()["rerouted_to_location_id"] == world.far


def test_stockout_keeps_other_tasks_reservations_in_the_bin(client, db, build):
    world = build()
    db.get(Inventory, (world.bin_a, world.task.sku_id)).qty_reserved = 7  # 3 belong to another task
    db.commit()

    report(client, world, type="stockout", qty_found=0)

    assert stock(world, world.bin_a) == (0, 3)


def test_no_bin_with_stock_leaves_the_task_for_the_supervisor(client, build):
    world = build(near_stock=0, far_stock=2)

    response = report(client, world, type="stockout", qty_found=0)

    assert response.status_code == 201
    body = response.json()
    assert (body["task_status"], body["rerouted_to_location_id"]) == ("exception", None)
    task = fresh(Task, world.task.id)
    assert (task.status, task.location_id) == (TaskStatus.exception, world.bin_a)
    assert stock(world, world.bin_a) == (0, 0)
    assert fresh(Worker, world.worker.id).status is WorkerStatus.idle
    assert fresh(TaskException, body["exception_id"]).resolved_at is None
    assert event_types()[-1] == "task_exception"


def test_rerouted_task_can_be_assigned_and_picked_to_finish_the_order(client, floor, build):
    world = build()
    report(client, world, type="stockout", qty_found=0)
    with SessionLocal() as session:
        result = assigner.run_pass(session)
    assert len(result.assignments) == 1
    made = result.assignments[0]

    response = client.post(f"/api/v1/tasks/{world.task.id}/pick", json={"assignment_id": made.assignment_id})

    assert response.status_code == 200, response.text
    assert response.json()["order_status"] == "complete"
    assert stock(world, world.near) == (16, 0)
    assert fresh(Order, floor.order_id).status is OrderStatus.complete


# --- worker down and recovery ---------------------------------------------------------------------


def test_worker_down_reopens_the_task_in_place(client, build):
    world = build()

    body = report(client, world, type="worker_down").json()

    assert (body["task_status"], body["rerouted_to_location_id"]) == ("open", None)
    assert fresh(Worker, world.worker.id).status is WorkerStatus.down
    assert fresh(Task, world.task.id).location_id == world.bin_a
    assert stock(world, world.bin_a) == (10, 4)
    assert fresh(TaskException, body["exception_id"]).resolved_at is not None
    assert event_types()[-2:] == ["worker_status_changed", "task_reopened"]


def test_a_down_worker_gets_no_work_until_recovered(client, build):
    world = build()
    report(client, world, type="worker_down")
    with SessionLocal() as session:
        assert assigner.run_pass(session).assignments == []

    response = client.post(f"/api/v1/simulation/workers/{world.worker.id}/recover")

    assert response.status_code == 200
    assert response.json() == {"worker_id": world.worker.id, "status": "idle"}
    with SessionLocal() as session:
        assert [a.worker_id for a in assigner.run_pass(session).assignments] == [world.worker.id]


def test_exception_and_recovery_do_not_bump_the_worker_version(client, build):
    world = build()
    version = fresh(Worker, world.worker.id).version

    report(client, world, type="worker_down")
    client.post(f"/api/v1/simulation/workers/{world.worker.id}/recover")

    assert fresh(Worker, world.worker.id).version == version


def test_recovering_a_worker_who_is_not_down_is_409(client, floor):
    worker = floor.worker(1, 1)

    assert_error(client.post(f"/api/v1/simulation/workers/{worker.id}/recover"), 409, "worker_not_down")


def test_recovering_an_unknown_worker_is_404(client, db):
    assert_error(client.post("/api/v1/simulation/workers/999999/recover"), 404, "worker_not_found")


# --- reassign closes a stuck task's exception -------------------------------------------------------


def test_reassigning_a_stuck_task_resolves_its_exception(client, floor, build):
    world = build(near_stock=0, far_stock=0)
    exception_id = report(client, world, type="jam").json()["exception_id"]
    target = floor.worker(5, 5)
    version = fresh(Task, world.task.id).version

    response = client.post(
        f"/api/v1/tasks/{world.task.id}/reassign", json={"worker_id": target.id, "expected_version": version}
    )

    assert response.status_code == 200, response.text
    assert fresh(TaskException, exception_id).resolved_at is not None
    assert client.get(LIST_URL, params={"open": "true"}).json() == {"items": [], "count": 0}
    assert "exception_resolved" in event_types()


def test_reassigning_a_healthy_task_records_no_resolution(client, floor, build):
    world = build()
    target = floor.worker(5, 5)
    version = fresh(Task, world.task.id).version

    client.post(f"/api/v1/tasks/{world.task.id}/reassign", json={"worker_id": target.id, "expected_version": version})

    assert "exception_resolved" not in event_types()


# --- conflicts and bad input ------------------------------------------------------------------------


def test_second_exception_on_the_same_assignment_is_409(client, build):
    world = build()
    assert report(client, world, type="jam").status_code == 201

    assert_error(report(client, world, type="jam"), 409, "assignment_not_active")

    assert exception_count() == 1


def test_exception_after_the_pick_is_409(client, build):
    world = build()
    client.post(f"/api/v1/tasks/{world.task.id}/pick", json={"assignment_id": world.assignment.id})

    assert_error(report(client, world, type="jam"), 409, "assignment_not_active")


def test_task_not_assigned_is_409(client, db, build):
    world = build()
    db.get(Task, world.task.id).status = TaskStatus.exception
    db.commit()

    assert_error(report(client, world, type="jam"), 409, "version_conflict")

    assert exception_count() == 0
    assert stock(world, world.bin_a) == (10, 4)


def test_failure_midway_rolls_everything_back(client, build, monkeypatch):
    world = build()
    version = fresh(Task, world.task.id).version

    def fail(*_args):
        raise service.ApiError(409, "boom", "failed midway")

    monkeypatch.setattr(service, "_update_worker_after_exception", fail)

    assert_error(report(client, world, type="stockout", qty_found=0), 409, "boom")

    task = fresh(Task, world.task.id)
    assert (task.status, task.location_id, task.version) == (TaskStatus.assigned, world.bin_a, version)
    assert fresh(Assignment, world.assignment.id).ended_at is None
    assert fresh(Worker, world.worker.id).status is WorkerStatus.busy
    assert stock(world, world.bin_a) == (10, 4)
    assert stock(world, world.near) == (20, 0)
    assert exception_count() == 0
    assert event_types() == []


def test_unknown_task_or_assignment_is_404(client, build):
    world = build()

    response = client.post("/api/v1/tasks/999999/exceptions", json={"type": "jam", "assignment_id": world.assignment.id})
    assert_error(response, 404, "task_not_found")
    response = client.post(f"/api/v1/tasks/{world.task.id}/exceptions", json={"type": "jam", "assignment_id": 999_999})
    assert_error(response, 404, "assignment_not_found")


def test_assignment_for_another_task_is_422(client, floor, build):
    world = build()
    other = floor.task(9, 9, status=TaskStatus.assigned)

    response = client.post(f"/api/v1/tasks/{other.id}/exceptions", json={"type": "jam", "assignment_id": world.assignment.id})

    assert_error(response, 422, "assignment_mismatch")


@pytest.mark.parametrize(
    "body",
    [
        {"type": "fire"},
        {"type": "stockout"},
        {"type": "stockout", "qty_found": -1},
        {"type": "jam", "qty_found": "lots"},
        {"type": "jam", "surprise": True},
        {"type": "jam", "assignment_id": 0},
    ],
)
def test_bad_body_is_422(client, build, body):
    world = build()

    assert_error(report(client, world, **body), 422, "validation_error")

    assert exception_count() == 0


def test_stockout_that_found_enough_is_422(client, build):
    world = build(qty=4)

    assert_error(report(client, world, type="stockout", qty_found=4), 422, "invalid_qty_found")

    assert exception_count() == 0


@pytest.mark.parametrize("round_", range(5))
def test_exception_racing_a_pick_on_one_task_has_one_winner(client, build, round_):
    world = build()
    start = Barrier(2)

    def run(call):
        start.wait()
        return call()

    calls = [
        lambda: report(client, world, type="jam"),
        lambda: client.post(f"/api/v1/tasks/{world.task.id}/pick", json={"assignment_id": world.assignment.id}),
    ]
    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(run, calls))

    assert sorted(r.status_code for r in responses)[1] == 409
    assert sorted(r.status_code for r in responses)[0] in (200, 201)
    assert fresh(Task, world.task.id).status in (TaskStatus.open, TaskStatus.picked)


# --- GET /api/v1/exceptions ---------------------------------------------------------------------------


def add_exception(db, world, type=ExceptionType.jam, minutes_ago=0, resolved=False):
    opened = utcnow() - timedelta(minutes=minutes_ago)
    exception = TaskException(
        task_id=world.task.id, assignment_id=world.assignment.id, type=type, from_location_id=world.bin_a,
        opened_at=opened, resolved_at=opened if resolved else None,
    )
    db.add(exception)
    db.commit()
    return exception


def test_list_open_is_only_unresolved_newest_first(client, db, floor, build):
    world = build()
    older = add_exception(db, world, minutes_ago=5)
    newer = add_exception(db, world, type=ExceptionType.stockout, minutes_ago=1)
    add_exception(db, world, resolved=True)

    body = client.get(LIST_URL, params={"open": "true"}).json()

    assert [item["exception_id"] for item in body["items"]] == [newer.id, older.id]
    assert body["count"] == 2
    first = body["items"][0]
    assert first["type"] == "stockout"
    assert first["order_id"] == floor.order_id
    assert first["task_status"] == "assigned"
    assert first["resolved_at"] is None
    assert ISO_MS_Z.match(first["opened_at"])


def test_list_resolved_and_all(client, db, build):
    world = build()
    add_exception(db, world)
    resolved = add_exception(db, world, resolved=True)

    assert [i["exception_id"] for i in client.get(LIST_URL, params={"open": "false"}).json()["items"]] == [resolved.id]
    assert client.get(LIST_URL).json()["count"] == 2


def test_list_limit(client, db, build):
    world = build()
    for minutes in range(3):
        add_exception(db, world, minutes_ago=minutes)

    assert client.get(LIST_URL, params={"limit": 2}).json()["count"] == 2


def test_list_empty(client, db):
    assert client.get(LIST_URL).json() == {"items": [], "count": 0}


@pytest.mark.parametrize("params", [{"open": "maybe"}, {"limit": 0}, {"limit": 501}])
def test_list_bad_params_are_422(client, db, params):
    assert_error(client.get(LIST_URL, params=params), 422, "validation_error")

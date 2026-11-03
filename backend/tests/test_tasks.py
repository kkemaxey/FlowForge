"""GET /api/v1/tasks and the transition() state machine, against the MySQL test database."""
from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.database import SessionLocal, utcnow
from app.modules.assignment.models import Assignment, AssignmentOutcome, AssignmentSource
from app.modules.orders.models import Order, OrderLine
from app.modules.tasks.models import Task, TaskStatus
from app.modules.tasks.service import ALLOWED_TRANSITIONS, TaskConflict, transition
from app.modules.warehouse.models import Location, LocationKind, Sku
from app.modules.workforce.models import Worker, WorkerKind

URL = "/api/v1/tasks"
T0 = datetime(2026, 11, 3, 12, 0, 0)


@pytest.fixture
def make_task(db):
    """Factory: make_task(status=..., priority=..., minutes=...) -> committed Task.

    All tasks hang off one order/line/SKU; `minutes` offsets created_at from T0 so tests control
    queue order. Each task gets its own bin at (n, 1).
    """
    sku = Sku(code="SKU-T", name="Test shoe")
    order = Order(external_ref="ORD-T")
    db.add_all([sku, order])
    db.flush()
    line = OrderLine(order_id=order.id, line_no=1, sku_id=sku.id, qty_ordered=1)
    db.add(line)
    db.flush()
    made = []

    def factory(status=TaskStatus.open, priority=0, minutes=0):
        location = Location(x=len(made), y=1, kind=LocationKind.storage, zone="A", aisle="A1")
        db.add(location)
        db.flush()
        task = Task(
            order_id=order.id, order_line_id=line.id, sku_id=sku.id, location_id=location.id, qty=1,
            status=status, priority=priority, created_at=T0 + timedelta(minutes=minutes),
        )
        db.add(task)
        db.commit()
        made.append(task)
        return task

    return factory


@pytest.fixture
def worker(db):
    w = Worker(name="W", kind=WorkerKind.human, x=0, y=0)
    db.add(w)
    db.commit()
    return w


def ids(response):
    return [item["task_id"] for item in response.json()["items"]]


# --- GET /api/v1/tasks ---------------------------------------------------------------------------


def test_open_queue_sorted_by_priority_then_oldest(client, make_task):
    old_low = make_task(priority=0, minutes=0)
    new_high = make_task(priority=5, minutes=10)
    new_low = make_task(priority=0, minutes=5)
    old_high = make_task(priority=5, minutes=1)

    response = client.get(URL, params={"status": "open"})

    assert response.status_code == 200
    assert ids(response) == [old_high.id, new_high.id, old_low.id, new_low.id]
    assert response.json()["count"] == 4


def test_status_filter(client, make_task):
    make_task(status=TaskStatus.open)
    picked = make_task(status=TaskStatus.picked)

    assert ids(client.get(URL, params={"status": "picked"})) == [picked.id]
    assert len(ids(client.get(URL))) == 2  # no filter: every task


def test_limit(client, make_task):
    tasks = [make_task(minutes=i) for i in range(5)]

    response = client.get(URL, params={"status": "open", "limit": 2})

    assert ids(response) == [tasks[0].id, tasks[1].id]
    assert response.json()["count"] == 2


@pytest.mark.parametrize(
    "params", [{"status": "done"}, {"limit": 0}, {"limit": 501}, {"limit": "x"}], ids=str
)
def test_bad_query_params_are_422(client, db, params):
    response = client.get(URL, params=params)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_item_shape_and_current_assignment(client, db, make_task, worker):
    task = make_task(status=TaskStatus.assigned, priority=2)
    assignment = Assignment(task_id=task.id, worker_id=worker.id, source=AssignmentSource.scheduler)
    db.add(assignment)
    db.commit()

    [item] = client.get(URL).json()["items"]

    assert item["task_id"] == task.id
    assert item["order_id"] == task.order_id
    assert item["order_line_id"] == task.order_line_id
    assert item["sku_code"] == "SKU-T"
    assert item["qty"] == 1
    assert item["location"] == {"location_id": task.location_id, "x": 0, "y": 1, "zone": "A", "aisle": "A1"}
    assert item["status"] == "assigned"
    assert item["priority"] == 2
    assert item["version"] == 0
    assert item["created_at"] == "2026-11-03T12:00:00.000Z"
    assert item["current_assignment"]["assignment_id"] == assignment.id
    assert item["current_assignment"]["worker_id"] == worker.id
    assert item["current_assignment"]["source"] == "scheduler"
    assert item["current_assignment"]["assigned_at"].endswith("Z")


def test_ended_assignment_is_not_current(client, db, make_task, worker):
    task = make_task(status=TaskStatus.open)
    db.add(
        Assignment(
            task_id=task.id, worker_id=worker.id, source=AssignmentSource.scheduler,
            ended_at=utcnow(), outcome=AssignmentOutcome.failed,
        )
    )
    db.commit()

    [item] = client.get(URL).json()["items"]

    assert item["current_assignment"] is None


# --- transition() --------------------------------------------------------------------------------


def reload(task_id):
    with SessionLocal() as fresh:
        return fresh.get(Task, task_id)


def test_transition_moves_status_and_bumps_version(db, make_task):
    task = make_task(status=TaskStatus.open)

    transition(db, task, TaskStatus.open, TaskStatus.assigned)
    db.commit()

    stored = reload(task.id)
    assert (stored.status, stored.version) == (TaskStatus.assigned, 1)
    assert (task.status, task.version) == (TaskStatus.assigned, 1)  # loaded object kept in sync


def test_transition_does_not_commit(db, make_task):
    task = make_task(status=TaskStatus.open)

    transition(db, task, TaskStatus.open, TaskStatus.assigned)
    db.rollback()

    stored = reload(task.id)
    assert (stored.status, stored.version) == (TaskStatus.open, 0)


def test_stale_version_conflicts(db, make_task):
    task = make_task(status=TaskStatus.open)

    with pytest.raises(TaskConflict) as error:
        transition(db, task, TaskStatus.open, TaskStatus.assigned, expected_version=7)

    assert error.value.status_code == 409
    assert error.value.code == "version_conflict"
    db.rollback()
    assert reload(task.id).version == 0


def test_task_already_moved_on_conflicts(db, make_task):
    task = make_task(status=TaskStatus.picked)

    # Caller believes the task is still assigned (and assigned -> picked is a legal move).
    with pytest.raises(TaskConflict) as error:
        transition(db, task, TaskStatus.assigned, TaskStatus.picked)

    assert error.value.code == "version_conflict"


def test_race_between_two_sessions_has_one_winner(db, make_task):
    task_id = make_task(status=TaskStatus.open).id
    with SessionLocal() as scheduler, SessionLocal() as supervisor:
        # Both read the task at version 0 ...
        mine, theirs = scheduler.get(Task, task_id), supervisor.get(Task, task_id)

        # ... the scheduler commits first ...
        transition(scheduler, mine, TaskStatus.open, TaskStatus.assigned)
        scheduler.commit()

        # ... so the supervisor's compare-and-set matches nothing.
        with pytest.raises(TaskConflict):
            transition(supervisor, theirs, TaskStatus.open, TaskStatus.assigned)
        supervisor.rollback()

    assert reload(task_id).version == 1


ALL_PAIRS = [(a, b) for a in TaskStatus for b in TaskStatus]


@pytest.mark.parametrize("from_status,to_status", ALL_PAIRS, ids=[f"{a.value}->{b.value}" for a, b in ALL_PAIRS])
def test_transition_rules(db, make_task, from_status, to_status):
    task = make_task(status=from_status)

    if to_status in ALLOWED_TRANSITIONS[from_status]:
        transition(db, task, from_status, to_status)
        db.commit()
        assert reload(task.id).status == to_status
    else:
        with pytest.raises(TaskConflict) as error:
            transition(db, task, from_status, to_status)
        assert error.value.code == "invalid_transition"
        db.rollback()
        stored = reload(task.id)
        assert (stored.status, stored.version) == (from_status, 0)


def test_expected_transition_table():
    """Guards the state machine against accidental edits."""
    assert ALLOWED_TRANSITIONS == {
        TaskStatus.open: {TaskStatus.assigned},
        TaskStatus.assigned: {TaskStatus.picked, TaskStatus.assigned, TaskStatus.open, TaskStatus.exception},
        TaskStatus.exception: {TaskStatus.open, TaskStatus.assigned},
        TaskStatus.picked: set(),
    }

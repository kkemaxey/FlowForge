import re

import pytest
from sqlalchemy import select, update

from app.core.errors import ApiError
from app.modules.assignment.models import Assignment
from app.modules.events.models import Event
from app.modules.simulation.models import TaskException
from app.modules.simulation.service import _compare_and_set
from app.modules.tasks.models import Task
from app.modules.workforce.models import Worker
from tests.sim_fixtures import api, build_world, db, db_engine, inventory_at, session_factory  # noqa: F401

ISO_MS_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def post_exception(api, world, **body):
    payload = {"assignment_id": world.assignment.id, **body}
    return api.post(f"/api/v1/tasks/{world.task.id}/exceptions", json=payload)


def event_types(db) -> list[str]:
    return [e.type for e in db.scalars(select(Event).order_by(Event.id))]


def test_stockout_reroutes_to_nearest_bin_with_stock(api, db):
    world = build_world(db)

    response = post_exception(api, world, type="stockout", qty_found=1)

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "stockout"
    assert body["task_id"] == world.task.id
    assert body["task_status"] == "open"
    assert body["rerouted_to_location_id"] == world.bin_near.id
    assert ISO_MS_UTC.match(body["opened_at"])

    db.expire_all()
    task = db.get(Task, world.task.id)
    assert (task.status, task.location_id, task.version) == ("open", world.bin_near.id, 2)
    assignment = db.get(Assignment, world.assignment.id)
    assert assignment.outcome == "failed" and assignment.ended_at is not None
    assert db.get(Worker, world.worker.id).status == "idle"

    old_bin, new_bin = inventory_at(db, world.bin_a), inventory_at(db, world.bin_near)
    assert (old_bin.on_hand, old_bin.reserved) == (1, 0)
    assert (new_bin.on_hand, new_bin.reserved) == (20, 4)
    assert inventory_at(db, world.bin_far).reserved == 0

    exc = db.get(TaskException, body["exception_id"])
    assert (exc.from_location_id, exc.qty_found, exc.run_id) == (world.bin_a.id, 1, world.run.id)
    assert exc.resolved_at == exc.opened_at, "a successful reroute is handled, so it is born resolved"
    assert event_types(db) == ["exception_opened", "worker_status_changed", "task_rerouted"]
    assert {e.run_id for e in db.scalars(select(Event))} == {world.run.id}


def test_reroute_skips_bins_without_enough_unreserved_stock(api, db):
    world = build_world(db, near_stock=3)

    body = post_exception(api, world, type="jam").json()

    assert body["rerouted_to_location_id"] == world.bin_far.id
    assert inventory_at(db, world.bin_far).reserved == 4


def test_jam_releases_reservation_without_touching_on_hand(api, db):
    world = build_world(db)

    post_exception(api, world, type="jam")

    old_bin = inventory_at(db, world.bin_a)
    assert (old_bin.on_hand, old_bin.reserved) == (10, 0)


def test_no_bin_with_stock_leaves_task_in_exception(api, db):
    world = build_world(db, near_stock=0, far_stock=2)

    response = post_exception(api, world, type="stockout", qty_found=0)

    assert response.status_code == 201
    body = response.json()
    assert body["task_status"] == "exception"
    assert body["rerouted_to_location_id"] is None
    db.expire_all()
    assert db.get(Task, world.task.id).location_id == world.bin_a.id
    assert inventory_at(db, world.bin_a).reserved == 0
    assert db.get(Worker, world.worker.id).status == "idle"
    assert event_types(db)[-1] == "task_exception"
    assert db.get(TaskException, body["exception_id"]).resolved_at is None, "waits for the supervisor"


def test_worker_down_reopens_task_in_place_and_parks_worker(api, db):
    world = build_world(db)

    body = post_exception(api, world, type="worker_down").json()

    assert (body["task_status"], body["rerouted_to_location_id"]) == ("open", None)
    db.expire_all()
    assert db.get(Worker, world.worker.id).status == "down"
    assert db.get(Task, world.task.id).location_id == world.bin_a.id
    assert inventory_at(db, world.bin_a).reserved == 4, "the bin is fine, so the reservation stays"
    assert event_types(db)[-1] == "task_reopened"


def test_second_exception_on_same_assignment_is_409(api, db):
    world = build_world(db)
    assert post_exception(api, world, type="jam").status_code == 201

    response = post_exception(api, world, type="jam")

    assert response.status_code == 409
    assert response.json()["code"] == "state_conflict"
    assert db.query(TaskException).count() == 1


def test_task_already_picked_is_409(api, db):
    world = build_world(db)
    db.execute(update(Task).values(status="picked"))
    db.commit()

    response = post_exception(api, world, type="jam")

    assert response.status_code == 409


def test_stale_version_is_409(db, session_factory):
    world = build_world(db)
    task = db.get(Task, world.task.id)
    with session_factory() as other:
        other.execute(update(Task).where(Task.id == task.id).values(version=Task.version + 1))
        other.commit()

    with pytest.raises(ApiError) as caught:
        _compare_and_set(db, Task, task, status="open")
    assert (caught.value.status_code, caught.value.code) == (409, "version_conflict")


def test_conflict_midway_rolls_back_everything(api, db, monkeypatch):
    """The worker row changes under us after inventory, task and assignment were updated; nothing may stick."""
    world = build_world(db)

    def bump_worker_first(session, model, row, *conditions, **values):
        if model is Worker:
            # Like a concurrent writer: change the row in the DB without refreshing our loaded copy.
            session.execute(
                update(Worker).where(Worker.id == row.id).values(version=Worker.version + 5)
                .execution_options(synchronize_session=False)
            )
        return _compare_and_set(session, model, row, *conditions, **values)

    monkeypatch.setattr("app.modules.simulation.service._compare_and_set", bump_worker_first)
    response = post_exception(api, world, type="stockout", qty_found=0)

    assert response.status_code == 409
    assert response.json()["code"] == "version_conflict"
    db.expire_all()
    assert db.get(Task, world.task.id).status == "assigned"
    assert db.get(Worker, world.worker.id).status == "busy"
    assert (inventory_at(db, world.bin_a).on_hand, inventory_at(db, world.bin_a).reserved) == (10, 4)
    assert inventory_at(db, world.bin_near).reserved == 0
    assert db.query(TaskException).count() == 0
    assert db.query(Event).count() == 0


def test_unknown_task_is_404(api, db):
    world = build_world(db)

    response = api.post("/api/v1/tasks/9999/exceptions", json={"type": "jam", "assignment_id": world.assignment.id})

    assert response.status_code == 404
    assert response.json() == {"detail": "Task 9999 not found", "code": "task_not_found"}


def test_unknown_assignment_is_404(api, db):
    world = build_world(db)

    response = api.post(f"/api/v1/tasks/{world.task.id}/exceptions", json={"type": "jam", "assignment_id": 9999})

    assert response.status_code == 404
    assert response.json()["code"] == "assignment_not_found"


@pytest.mark.parametrize(
    "body",
    [
        {"type": "fire"},
        {"type": "stockout"},  # qty_found required
        {"type": "stockout", "qty_found": -1},
        {"type": "jam", "qty_found": "lots"},
        {"type": "jam", "surprise": True},
        {"type": "stockout", "qty_found": 4},  # not short: task qty is 4
        {"type": "jam", "assignment_id": 0},
    ],
)
def test_bad_input_is_422(api, db, body):
    world = build_world(db)

    response = api.post(f"/api/v1/tasks/{world.task.id}/exceptions", json={"assignment_id": world.assignment.id, **body})

    assert response.status_code == 422
    assert set(response.json()) == {"detail", "code"}
    assert db.query(TaskException).count() == 0


def test_assignment_for_another_task_is_422(api, db):
    world = build_world(db)
    other = Task(
        order_id=world.order.id, order_line_id=world.task.order_line_id, sku_id=world.sku.id,
        location_id=world.bin_near.id, qty=1, status="assigned",
    )
    db.add(other)
    db.commit()

    response = api.post(f"/api/v1/tasks/{other.id}/exceptions", json={"type": "jam", "assignment_id": world.assignment.id})

    assert response.status_code == 422
    assert response.json()["code"] == "assignment_mismatch"


def test_requires_auth(db):
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).post("/api/v1/tasks/1/exceptions", json={"type": "jam", "assignment_id": 1})

    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"

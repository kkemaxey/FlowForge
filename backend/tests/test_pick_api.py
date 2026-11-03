from sqlalchemy import select

from app.modules.assignment.models import Assignment
from app.modules.events.models import Event
from app.modules.orders.models import Order
from app.modules.tasks.models import Task
from app.modules.workforce.models import Worker
from tests.sim_fixtures import api, build_world, db, db_engine, inventory_at, session_factory  # noqa: F401


def pick(api, task_id, assignment_id):
    return api.post(f"/api/v1/tasks/{task_id}/pick", json={"assignment_id": assignment_id})


def test_pick_last_task_completes_order(api, db):
    world = build_world(db)

    response = pick(api, world.task.id, world.assignment.id)

    assert response.status_code == 200
    body = response.json()
    assert (body["task_status"], body["order_status"]) == ("complete", "complete")
    assert body["picked_at"].endswith("Z")

    db.expire_all()
    assert db.get(Order, world.order.id).completed_at is not None
    assignment = db.get(Assignment, world.assignment.id)
    assert assignment.outcome == "completed"
    worker = db.get(Worker, world.worker.id)
    assert (worker.status, worker.x, worker.y) == ("idle", world.bin_a.x, world.bin_a.y)
    stock = inventory_at(db, world.bin_a)
    assert (stock.on_hand, stock.reserved) == (6, 0)
    assert [e.type for e in db.scalars(select(Event).order_by(Event.id))] == [
        "task_picked", "worker_status_changed", "order_completed",
    ]


def test_order_waits_for_its_other_tasks(api, db):
    world = build_world(db)
    second = Task(
        order_id=world.order.id, order_line_id=world.task.order_line_id, sku_id=world.sku.id,
        location_id=world.bin_near.id, qty=1, status="open",
    )
    db.add(second)
    db.commit()

    body = pick(api, world.task.id, world.assignment.id).json()

    assert (body["task_status"], body["order_status"]) == ("picked", "in_progress")
    assert "order_completed" not in {e.type for e in db.scalars(select(Event))}


def test_pick_twice_is_409(api, db):
    world = build_world(db)
    pick(api, world.task.id, world.assignment.id)

    response = pick(api, world.task.id, world.assignment.id)

    assert response.status_code == 409
    assert response.json()["code"] == "state_conflict"


def test_pick_from_short_bin_is_409_and_changes_nothing(api, db):
    world = build_world(db)
    stock = inventory_at(db, world.bin_a)
    stock.on_hand = 2
    db.commit()

    response = pick(api, world.task.id, world.assignment.id)

    assert response.status_code == 409
    assert response.json()["code"] == "insufficient_stock"
    db.expire_all()
    assert db.get(Task, world.task.id).status == "assigned"
    assert db.scalar(select(Event)) is None


def test_pick_unknown_task_is_404_and_bad_body_is_422(api, db):
    world = build_world(db)

    assert pick(api, 9999, world.assignment.id).status_code == 404
    assert api.post(f"/api/v1/tasks/{world.task.id}/pick", json={}).status_code == 422

"""POST /api/v1/orders/{order_id}/expedite."""
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.events.models import Event
from app.modules.orders.models import Order, OrderStatus
from app.modules.orders.service import EXPEDITE_PRIORITY
from app.modules.tasks.models import Task, TaskStatus


def url(order_id):
    return f"/api/v1/orders/{order_id}/expedite"


def fresh(model, id_):
    with SessionLocal() as session:
        return session.get(model, id_)


def test_expedite_marks_order_and_raises_unfinished_tasks(client, db, floor):
    order = floor.order(priority=2)
    open_task = floor.task(1, 1, priority=2, order=order)
    assigned = floor.task(2, 2, priority=2, order=order, status=TaskStatus.assigned)
    picked = floor.task(3, 3, priority=2, order=order, status=TaskStatus.picked)

    response = client.post(url(order.id))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["order_id"] == order.id
    assert body["expedited"] is True
    assert body["priority"] == EXPEDITE_PRIORITY

    stored = fresh(Order, order.id)
    assert (stored.expedited, stored.priority, stored.version) == (True, EXPEDITE_PRIORITY, 1)
    assert fresh(Task, open_task.id).priority == EXPEDITE_PRIORITY
    assert fresh(Task, assigned.id).priority == EXPEDITE_PRIORITY
    assert fresh(Task, picked.id).priority == 2  # finished work is left alone
    assert fresh(Task, open_task.id).version == 0  # not a status change, so no version bump

    db.rollback()
    [event] = db.scalars(select(Event)).all()
    assert (event.event_type, event.order_id, event.run_id) == ("order_expedited", order.id, floor.run_id)
    assert event.payload == {"priority": EXPEDITE_PRIORITY, "tasks_raised": 2}


def test_expedited_tasks_jump_the_queue(client, floor):
    older = floor.task(1, 1, minutes=0)
    rush_order = floor.order()
    rush = floor.task(2, 2, minutes=10, order=rush_order)

    before = [i["task_id"] for i in client.get("/api/v1/tasks", params={"status": "open"}).json()["items"]]
    client.post(url(rush_order.id))
    after = [i["task_id"] for i in client.get("/api/v1/tasks", params={"status": "open"}).json()["items"]]

    assert before == [older.id, rush.id]
    assert after == [rush.id, older.id]


def test_expedite_does_not_change_who_is_assigned(client, floor):
    """Known MVP shortcoming: greedy_v1 is pure distance, so a nearer normal task still wins."""
    near = floor.task(1, 0)
    rush_order = floor.order()
    floor.task(9, 9, order=rush_order)
    worker = floor.worker(0, 0)
    client.post(url(rush_order.id))

    made = client.post("/api/v1/assignments/run", json={}).json()["assignments"]

    assert [(a["worker_id"], a["task_id"]) for a in made] == [(worker.id, near.id)]


def test_expediting_twice_is_a_no_op(client, db, floor):
    order = floor.order()
    floor.task(1, 1, order=order)

    first = client.post(url(order.id))
    second = client.post(url(order.id))

    assert second.status_code == 200
    assert second.json() == first.json()
    assert fresh(Order, order.id).version == 1
    db.rollback()
    assert len(db.scalars(select(Event)).all()) == 1


def test_complete_order_is_409(client, floor):
    order = floor.order(status=OrderStatus.complete)

    response = client.post(url(order.id))

    assert response.status_code == 409
    assert response.json()["code"] == "order_complete"
    assert fresh(Order, order.id).expedited is False


def test_missing_order_is_404(client, db):
    response = client.post(url(9999))

    assert response.status_code == 404
    assert response.json()["code"] == "order_not_found"

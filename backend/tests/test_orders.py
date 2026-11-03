"""POST /api/v1/orders, GET /api/v1/orders and GET /api/v1/orders/{id} against the MySQL test database."""
import re
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.event import listen, remove

from app.core.database import engine
from app.modules.events.models import Event
from app.modules.orders.models import Order, OrderLine, OrderStatus
from app.modules.simulation.models import SimRun
from app.modules.tasks.models import Task
from app.modules.warehouse.models import Inventory, Location, LocationKind, Sku

URL = "/api/v1/orders"
ISO_MS_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


@pytest.fixture
def warehouse(db):
    """Small known warehouse. Returns {"run_id", "bins": {name: location_id}}.

    SKU-A: bin a1 holds 10.
    SKU-B: bins b1 (4), b2 (3), b3 (2). No bin alone covers 5, so 5 units split.
    SKU-C: bins c1 (2), c2 (6). c2 alone covers 5.
    SKU-D: bin d1 holds 5 with 4 already reserved, so 1 is available.
    """
    layout = {
        "a1": (1, 1, "SKU-A", 10, 0),
        "b1": (1, 2, "SKU-B", 4, 0),
        "b2": (2, 2, "SKU-B", 3, 0),
        "b3": (4, 7, "SKU-B", 2, 0),
        "c1": (1, 3, "SKU-C", 2, 0),
        "c2": (2, 3, "SKU-C", 6, 0),
        "d1": (1, 4, "SKU-D", 5, 4),
    }
    skus = {code: Sku(code=code, name=code) for code in ("SKU-A", "SKU-B", "SKU-C", "SKU-D")}
    run = SimRun(algorithm="greedy_v1", seed=1, order_rate=1.0)
    db.add_all([*skus.values(), run])
    bins = {}
    for name, (x, y, code, on_hand, reserved) in layout.items():
        location = Location(x=x, y=y, kind=LocationKind.storage, zone="A" if y <= 4 else "B", aisle="A1")
        db.add(location)
        db.flush()
        db.add(Inventory(location_id=location.id, sku_id=skus[code].id, qty_on_hand=on_hand, qty_reserved=reserved))
        bins[name] = location.id
    db.commit()
    return {"run_id": run.id, "bins": bins}


def order_body(warehouse, ref="ORD-1", lines=None, **extra):
    if lines is None:
        lines = [{"sku_code": "SKU-A", "qty": 2}]
    body = {"external_ref": ref, "run_id": warehouse["run_id"], "lines": lines}
    body.update(extra)
    return body


def count(db, model) -> int:
    db.rollback()  # end the session's snapshot so rows written by the API are visible
    return db.scalar(select(func.count()).select_from(model))


def reserved(db, location_id) -> int:
    db.rollback()
    return db.scalar(select(Inventory.qty_reserved).where(Inventory.location_id == location_id))


def assert_error(response, status_code, code):
    assert response.status_code == status_code, response.text
    body = response.json()
    assert body["code"] == code
    assert isinstance(body["detail"], str) and body["detail"]


def test_create_order_single_bin(client, db, warehouse):
    response = client.post(
        URL, json=order_body(warehouse, priority=3, due_at="2026-10-20T17:00:00.000Z")
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["external_ref"] == "ORD-1"
    assert body["run_id"] == warehouse["run_id"]
    assert body["status"] == "open"
    assert body["priority"] == 3
    assert body["expedited"] is False
    assert body["due_at"] == "2026-10-20T17:00:00.000Z"
    assert ISO_MS_Z.match(body["created_at"])

    [line] = body["lines"]
    assert line["sku_code"] == "SKU-A"
    assert line["qty_ordered"] == 2
    [task] = line["tasks"]
    assert task["qty"] == 2
    assert task["status"] == "open"
    assert task["version"] == 0
    assert task["location"] == {
        "location_id": warehouse["bins"]["a1"], "x": 1, "y": 1, "kind": "storage", "zone": "A", "aisle": "A1"
    }
    assert reserved(db, warehouse["bins"]["a1"]) == 2


def test_tasks_copy_order_priority(client, db, warehouse):
    client.post(URL, json=order_body(warehouse, priority=5))

    db.rollback()
    assert db.scalars(select(Task.priority)).all() == [5]


def test_line_splits_across_bins_when_no_single_bin_covers_it(client, db, warehouse):
    response = client.post(URL, json=order_body(warehouse, lines=[{"sku_code": "SKU-B", "qty": 5}]))

    assert response.status_code == 201, response.text
    tasks = response.json()["lines"][0]["tasks"]
    bins = warehouse["bins"]
    # Largest unreserved stock first: all 4 from b1, the remaining 1 from b2.
    assert [(t["location"]["location_id"], t["qty"]) for t in tasks] == [(bins["b1"], 4), (bins["b2"], 1)]
    assert reserved(db, bins["b1"]) == 4
    assert reserved(db, bins["b2"]) == 1
    assert reserved(db, bins["b3"]) == 0


def test_single_bin_preferred_when_one_covers_the_line(client, db, warehouse):
    response = client.post(URL, json=order_body(warehouse, lines=[{"sku_code": "SKU-C", "qty": 5}]))

    tasks = response.json()["lines"][0]["tasks"]
    assert [(t["location"]["location_id"], t["qty"]) for t in tasks] == [(warehouse["bins"]["c2"], 5)]


def test_existing_reservations_are_respected(client, db, warehouse):
    ok = client.post(URL, json=order_body(warehouse, ref="ORD-1", lines=[{"sku_code": "SKU-D", "qty": 1}]))
    rejected = client.post(URL, json=order_body(warehouse, ref="ORD-2", lines=[{"sku_code": "SKU-D", "qty": 1}]))

    assert ok.status_code == 201
    assert_error(rejected, 409, "insufficient_stock")
    assert reserved(db, warehouse["bins"]["d1"]) == 5


def test_same_sku_on_two_lines_reserves_cumulatively(client, db, warehouse):
    lines = [{"sku_code": "SKU-A", "qty": 6}, {"sku_code": "SKU-A", "qty": 4}]
    response = client.post(URL, json=order_body(warehouse, lines=lines))

    assert response.status_code == 201, response.text
    assert reserved(db, warehouse["bins"]["a1"]) == 10


def test_replay_returns_existing_order_and_writes_nothing(client, db, warehouse):
    first = client.post(URL, json=order_body(warehouse))
    counts = {model: count(db, model) for model in (Order, OrderLine, Task, Event)}

    # Same external_ref, different body: the stored order wins.
    replay = client.post(URL, json=order_body(warehouse, lines=[{"sku_code": "SKU-A", "qty": 9}]))

    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert {model: count(db, model) for model in counts} == counts
    assert reserved(db, warehouse["bins"]["a1"]) == 2


def test_events_written_in_same_transaction(client, db, warehouse):
    response = client.post(URL, json=order_body(warehouse, lines=[{"sku_code": "SKU-B", "qty": 5}]))
    order_id = response.json()["order_id"]
    task_ids = [t["task_id"] for t in response.json()["lines"][0]["tasks"]]

    db.rollback()
    events = db.scalars(select(Event).order_by(Event.id)).all()
    assert [e.event_type for e in events] == ["order_received", "task_created", "task_created"]
    assert all(e.order_id == order_id and e.run_id == warehouse["run_id"] for e in events)
    assert [e.task_id for e in events[1:]] == task_ids


def test_insufficient_stock_rolls_back_the_whole_order(client, db, warehouse):
    # Line 1 is fine on its own; line 2 asks for more SKU-B (9 total) than exists.
    lines = [{"sku_code": "SKU-A", "qty": 3}, {"sku_code": "SKU-B", "qty": 10}]
    response = client.post(URL, json=order_body(warehouse, lines=lines))

    assert_error(response, 409, "insufficient_stock")
    assert "SKU-B" in response.json()["detail"]
    for model in (Order, OrderLine, Task, Event):
        assert count(db, model) == 0
    assert reserved(db, warehouse["bins"]["a1"]) == 0


@pytest.mark.parametrize(
    "lines",
    [
        [],
        [{"sku_code": "SKU-A", "qty": 0}],
        [{"sku_code": "SKU-A", "qty": -1}],
        [{"sku_code": "SKU-A"}],
    ],
    ids=["empty-lines", "qty-zero", "qty-negative", "qty-missing"],
)
def test_invalid_lines_rejected(client, db, warehouse, lines):
    response = client.post(URL, json=order_body(warehouse, lines=lines))

    assert_error(response, 422, "validation_error")
    assert count(db, Order) == 0


def test_unknown_sku_rejected_and_nothing_written(client, db, warehouse):
    lines = [{"sku_code": "SKU-A", "qty": 1}, {"sku_code": "SKU-NOPE", "qty": 1}]
    response = client.post(URL, json=order_body(warehouse, lines=lines))

    assert_error(response, 422, "unknown_sku")
    assert "SKU-NOPE" in response.json()["detail"]
    assert count(db, Order) == 0
    assert count(db, Event) == 0
    assert reserved(db, warehouse["bins"]["a1"]) == 0


def test_unknown_run_rejected(client, db, warehouse):
    response = client.post(URL, json=order_body(warehouse, run_id=999))

    assert_error(response, 422, "unknown_run")
    assert count(db, Order) == 0


def test_get_order_returns_lines_and_tasks(client, db, warehouse):
    created = client.post(URL, json=order_body(warehouse, lines=[{"sku_code": "SKU-B", "qty": 5}])).json()

    response = client.get(f"{URL}/{created['order_id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_missing_order_is_404(client, db):
    assert_error(client.get(f"{URL}/12345"), 404, "order_not_found")


def test_list_orders_empty(client, db):
    response = client.get(URL)

    assert response.status_code == 200
    assert response.json() == {"items": [], "count": 0}


def test_list_orders_newest_first_with_id_breaking_ties(client, db, floor):
    t0 = datetime(2026, 11, 3, 12, 0, 0)
    oldest, tied_low, tied_high, newest = [floor.order() for _ in range(4)]
    oldest.created_at = t0
    tied_low.created_at = t0 + timedelta(minutes=1)
    tied_high.created_at = t0 + timedelta(minutes=1)
    newest.created_at = t0 + timedelta(minutes=2)
    db.get(Order, floor.order_id).created_at = t0 - timedelta(minutes=1)
    db.commit()

    body = client.get(URL).json()

    assert [item["order_id"] for item in body["items"]] == [
        newest.id, tied_high.id, tied_low.id, oldest.id, floor.order_id,
    ]
    assert body["count"] == 5


def test_list_orders_limit_keeps_the_newest(client, db, floor):
    t0 = datetime(2026, 11, 3, 12, 0, 0)
    orders = [floor.order() for _ in range(3)]
    for minutes, order in enumerate(orders):
        order.created_at = t0 + timedelta(minutes=minutes)
    db.get(Order, floor.order_id).created_at = t0 - timedelta(minutes=1)
    db.commit()

    body = client.get(URL, params={"limit": 2}).json()

    assert [item["order_id"] for item in body["items"]] == [orders[2].id, orders[1].id]
    assert body["count"] == 2


def test_list_orders_default_limit_is_50(client, db, floor):
    for _ in range(50):
        floor.order()  # 51 orders with the one floor starts with

    assert client.get(URL).json()["count"] == 50


@pytest.mark.parametrize("limit", [0, 501, "many"])
def test_list_orders_bad_limit_is_422(client, db, limit):
    assert_error(client.get(URL, params={"limit": limit}), 422, "validation_error")


def test_order_completed_at_is_returned(client, db, floor):
    finished = floor.order(status=OrderStatus.complete)
    finished.completed_at = datetime(2026, 11, 3, 12, 30, 0)
    db.commit()

    items = {item["order_id"]: item for item in client.get(URL).json()["items"]}

    assert items[finished.id]["completed_at"] == "2026-11-03T12:30:00.000Z"
    assert items[floor.order_id]["completed_at"] is None
    assert client.get(f"{URL}/{finished.id}").json()["completed_at"] == "2026-11-03T12:30:00.000Z"


def test_list_orders_keeps_lines_and_tasks_on_the_right_order(client, db, warehouse):
    bodies = [
        order_body(warehouse, ref="ORD-A"),
        order_body(warehouse, ref="ORD-B", lines=[{"sku_code": "SKU-B", "qty": 5}]),
        order_body(warehouse, ref="ORD-C", lines=[{"sku_code": "SKU-C", "qty": 5}, {"sku_code": "SKU-A", "qty": 1}]),
    ]
    created = {}
    for body in bodies:
        order = client.post(URL, json=body).json()
        created[order["order_id"]] = order

    listed = client.get(URL).json()["items"]

    assert {item["order_id"]: item for item in listed} == created


def test_list_orders_query_count_does_not_grow_with_orders(client, db, warehouse):
    def selects_for_list() -> int:
        statements = []

        def record(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        listen(engine, "before_cursor_execute", record)
        try:
            assert client.get(URL).status_code == 200
        finally:
            remove(engine, "before_cursor_execute", record)
        return len(statements)

    client.post(URL, json=order_body(warehouse, ref="ORD-1", lines=[{"sku_code": "SKU-A", "qty": 1}]))
    with_one_order = selects_for_list()
    for ref in ("ORD-2", "ORD-3", "ORD-4"):
        client.post(URL, json=order_body(warehouse, ref=ref, lines=[{"sku_code": "SKU-A", "qty": 1}]))

    assert selects_for_list() == with_one_order

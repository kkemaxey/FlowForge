"""GET /api/v1/events/metrics and /metrics/throughput against the MySQL test database."""
from datetime import datetime, timedelta

import pytest

from app.modules.events import service
from app.modules.events.models import Event
from app.modules.simulation.models import ExceptionType, TaskException
from app.modules.tasks.models import TaskStatus
from app.modules.warehouse.models import Inventory, Location
from app.modules.workforce.models import WorkerStatus

METRICS = "/api/v1/events/metrics"
THROUGHPUT = "/api/v1/events/metrics/throughput"
NOW = datetime(2026, 11, 3, 12, 30, 20, 500000)


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    monkeypatch.setattr(service, "utcnow", lambda: NOW)


def add_pick(db, seconds_ago, qty=1, event_type="task_picked"):
    db.add(Event(event_type=event_type, occurred_at=NOW - timedelta(seconds=seconds_ago), payload={"qty": qty}))
    db.commit()


def add_exception(db, floor, x=4, minutes_ago=0, resolved=False, aisle="A2", zone="A"):
    """A stockout on a new task, whose bin is at (x, 2)."""
    task = floor.task(x, 2)
    location = db.get(Location, task.location_id)
    location.aisle, location.zone = aisle, zone
    opened = NOW - timedelta(minutes=minutes_ago)
    db.add(TaskException(
        task_id=task.id, type=ExceptionType.stockout, from_location_id=location.id, opened_at=opened,
        resolved_at=opened if resolved else None,
    ))
    db.commit()
    return task


# --- /metrics ---------------------------------------------------------------------------------------


def test_metrics_with_nothing_happening(client, db):
    assert client.get(METRICS).json() == {
        "units_per_hour": 0, "tasks_per_hour": 0, "active_exception": None, "as_of": "2026-11-03T12:30:20.500Z",
    }


def test_rates_scale_the_last_five_minutes_to_an_hour(client, db):
    add_pick(db, 10, qty=2)
    add_pick(db, 299, qty=3)

    body = client.get(METRICS).json()

    assert body["tasks_per_hour"] == 24
    assert body["units_per_hour"] == 60


def test_rates_ignore_older_picks_and_other_events(client, db):
    add_pick(db, 301, qty=5)
    add_pick(db, 10, qty=5, event_type="task_assigned")

    body = client.get(METRICS).json()

    assert (body["tasks_per_hour"], body["units_per_hour"]) == (0, 0)


def test_active_exception_is_the_newest_open_one(client, db, floor):
    add_exception(db, floor, x=1, minutes_ago=5)
    task = add_exception(db, floor, x=4, minutes_ago=1)
    add_exception(db, floor, x=7, minutes_ago=0, resolved=True)

    assert client.get(METRICS).json()["active_exception"] == {
        "task_id": task.id,
        "order_id": floor.order_id,
        "location": "A2 (4,2)",
        "type": "stockout",
        "raised_at": "2026-11-03T12:29:20.500Z",
    }


@pytest.mark.parametrize("aisle, zone, label", [(None, "B", "B (4,2)"), (None, None, "? (4,2)")])
def test_location_label_matches_the_board(client, db, floor, aisle, zone, label):
    add_exception(db, floor, aisle=aisle, zone=zone)

    assert client.get(METRICS).json()["active_exception"]["location"] == label


# --- /metrics/throughput ------------------------------------------------------------------------------


def test_throughput_has_one_bucket_per_minute_oldest_first(client, db):
    body = client.get(THROUGHPUT, params={"minutes": 3}).json()

    assert body == [
        {"bucket_start": "2026-11-03T12:28:00.000Z", "units": 0, "tasks": 0},
        {"bucket_start": "2026-11-03T12:29:00.000Z", "units": 0, "tasks": 0},
        {"bucket_start": "2026-11-03T12:30:00.000Z", "units": 0, "tasks": 0},
    ]


def test_throughput_sums_picks_into_their_minutes(client, db):
    add_pick(db, 5, qty=2)  # 12:30:15
    add_pick(db, 10, qty=3)  # 12:30:10
    add_pick(db, 30, qty=1)  # 12:29:50
    add_pick(db, 120, qty=9)  # 12:28:20, before the window
    add_pick(db, 5, qty=4, event_type="task_assigned")

    body = client.get(THROUGHPUT, params={"minutes": 2}).json()

    assert [(b["units"], b["tasks"]) for b in body] == [(1, 1), (5, 2)]


def test_throughput_defaults_to_30_minutes(client, db):
    assert len(client.get(THROUGHPUT).json()) == 30


@pytest.mark.parametrize("minutes", [0, 1441, "many"])
def test_throughput_bad_minutes_is_422(client, db, minutes):
    response = client.get(THROUGHPUT, params={"minutes": minutes})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_a_real_pick_counts(client, db, floor, monkeypatch):
    """The event the pick endpoint writes is the one the metrics read."""
    task = floor.task(1, 1, status=TaskStatus.assigned)
    task.qty = 3
    db.add(Inventory(location_id=task.location_id, sku_id=task.sku_id, qty_on_hand=9, qty_reserved=3))
    db.commit()
    assignment = floor.assign(task, floor.worker(0, 0, status=WorkerStatus.busy))
    assert client.post(f"/api/v1/tasks/{task.id}/pick", json={"assignment_id": assignment.id}).status_code == 200
    db.rollback()
    picked_at = db.query(Event).filter_by(event_type="task_picked").one().occurred_at
    monkeypatch.setattr(service, "utcnow", lambda: picked_at + timedelta(seconds=1))

    body = client.get(METRICS).json()
    assert (body["tasks_per_hour"], body["units_per_hour"]) == (12, 36)

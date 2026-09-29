from datetime import datetime, timedelta

import pytest

from app.core.exceptions import RuleViolationError
from app.modules.metrics.service import (
    EventRecord,
    MetricsService,
    WorkerCounts,
    count_exceptions,
    count_workers,
    throughput_per_hour,
    units_picked,
    work_in_progress,
)
from tests.unit.fakes import FakeEventRepository, FakeWorkerRepository, make_worker

NOW = datetime(2026, 9, 29, 12, 0, 0)


def event(event_type, task_id=None, qty=None, minutes_ago=0, event_id=1):
    return EventRecord(id=event_id, ts=NOW - timedelta(minutes=minutes_ago), type=event_type,
                       task_id=task_id, worker_id=None, qty=qty, payload=None)


def build_service(workers=()):
    events = FakeEventRepository()
    service = MetricsService(events, FakeWorkerRepository(workers), clock=lambda: NOW)
    return service, events


# --- pure metric functions ---

def test_units_picked_sums_qty_of_pick_events_only():
    events = [
        event("task_picked", task_id=1, qty=3),
        event("task_picked", task_id=2, qty=4),
        event("task_assigned", task_id=3),
        event("task_exception", task_id=4),
    ]

    assert units_picked(events) == 7


@pytest.mark.parametrize("units, window, expected", [
    (30, 30, 60.0),
    (7, 60, 7.0),
    (10, 45, 13.3),
    (0, 60, 0.0),
])
def test_throughput_per_hour_scales_to_an_hour(units, window, expected):
    assert throughput_per_hour(units, window) == expected


def test_count_exceptions():
    events = [event("task_exception", task_id=1), event("task_picked", task_id=2, qty=1),
              event("task_exception", task_id=3)]

    assert count_exceptions(events) == 2


def test_wip_counts_tasks_whose_latest_event_is_assigned():
    task_events = [
        event("task_assigned", task_id=1),
        event("task_assigned", task_id=2), event("task_picked", task_id=2, qty=1),
        event("task_assigned", task_id=3), event("task_exception", task_id=3),
        event("task_assigned", task_id=4), event("task_exception", task_id=4),
        event("task_assigned", task_id=4),
    ]

    assert work_in_progress(task_events) == 2  # tasks 1 and 4


def test_wip_ignores_non_task_events():
    assert work_in_progress([event("order_completed", task_id=9)]) == 0


def test_count_workers_puts_disabled_workers_in_their_own_bucket():
    workers = [
        make_worker(id=1, status="idle", enabled=True),
        make_worker(id=2, status="idle", enabled=True),
        make_worker(id=3, status="busy", enabled=True),
        make_worker(id=4, status="busy", enabled=False),
    ]

    assert count_workers(workers) == WorkerCounts(idle=2, busy=1, disabled=1)


# --- MetricsService.record_event ---

def test_record_event_stamps_server_time():
    service, events = build_service()

    recorded = service.record_event("task_picked", task_id=5, worker_id=2, qty=3)

    assert recorded.ts == NOW
    assert events.events == [recorded]


def test_record_event_allows_order_completed_without_task_id():
    service, _ = build_service()

    recorded = service.record_event("order_completed", payload={"order_id": 7})

    assert recorded.payload == {"order_id": 7}


def test_record_event_rejects_unknown_type():
    service, _ = build_service()

    with pytest.raises(RuleViolationError) as error:
        service.record_event("robot_danced", task_id=1)

    assert error.value.code == "unknown_event_type"


@pytest.mark.parametrize("event_type", ["task_assigned", "task_picked", "task_exception"])
def test_task_events_require_task_id(event_type):
    service, _ = build_service()

    with pytest.raises(RuleViolationError) as error:
        service.record_event(event_type, qty=1)

    assert error.value.code == "task_id_required"


@pytest.mark.parametrize("qty", [None, 0])
def test_pick_events_require_positive_qty(qty):
    service, _ = build_service()

    with pytest.raises(RuleViolationError) as error:
        service.record_event("task_picked", task_id=1, qty=qty)

    assert error.value.code == "qty_required"


# --- MetricsService.snapshot ---

def test_snapshot_only_counts_events_inside_the_window():
    service, events = build_service(workers=[make_worker(id=1, status="idle")])
    events.add("task_picked", NOW - timedelta(minutes=90), 1, None, 50, None)
    events.add("task_picked", NOW - timedelta(minutes=10), 2, None, 6, None)
    events.add("task_exception", NOW - timedelta(minutes=5), 3, None, None, None)
    events.add("task_assigned", NOW - timedelta(minutes=1), 4, None, None, None)

    snapshot = service.snapshot(window_minutes=60)

    assert snapshot.window_minutes == 60
    assert snapshot.units_picked == 6
    assert snapshot.throughput_per_hour == 6.0
    assert snapshot.exceptions == 1
    assert snapshot.wip == 1
    assert snapshot.workers == WorkerCounts(idle=1, busy=0, disabled=0)


@pytest.mark.parametrize("window", [1, 1440])
def test_snapshot_accepts_window_boundaries(window):
    service, _ = build_service()

    assert service.snapshot(window_minutes=window).window_minutes == window


@pytest.mark.parametrize("window", [0, -5, 1441])
def test_snapshot_rejects_out_of_range_window(window):
    service, _ = build_service()

    with pytest.raises(RuleViolationError) as error:
        service.snapshot(window_minutes=window)

    assert error.value.code == "invalid_window"

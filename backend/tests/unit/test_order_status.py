from datetime import datetime, timedelta

import pytest

from app.modules.orders.order_status import OrderStatus, effective_status, progress_status

NOW = datetime(2026, 10, 1, 14, 0, 0)


@pytest.mark.parametrize("task_statuses, expected", [
    (["open", "open"], OrderStatus.NEW),
    (["assigned", "open"], OrderStatus.IN_PROGRESS),
    (["picked", "open"], OrderStatus.IN_PROGRESS),
    (["exception"], OrderStatus.IN_PROGRESS),
    (["picked", "picked"], OrderStatus.COMPLETE),
])
def test_progress_status_follows_the_tasks(task_statuses, expected):
    assert progress_status(task_statuses) == expected


def test_unfinished_order_past_due_is_late():
    assert effective_status("in_progress", NOW - timedelta(minutes=1), NOW) == OrderStatus.LATE
    assert effective_status("new", NOW - timedelta(minutes=1), NOW) == OrderStatus.LATE


def test_complete_order_is_never_late():
    assert effective_status("complete", NOW - timedelta(hours=2), NOW) == OrderStatus.COMPLETE


def test_order_before_due_keeps_its_status():
    assert effective_status("new", NOW + timedelta(minutes=5), NOW) == OrderStatus.NEW

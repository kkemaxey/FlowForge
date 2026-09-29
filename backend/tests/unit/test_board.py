from datetime import datetime, timedelta

from app.modules.orders.board import build_live_board, is_late, minutes_until_due
from app.modules.orders.models import AssignmentRecord, OrderLineRecord, OrderRecord, TaskRecord
from app.modules.orders.order_status import OrderStatus
from app.modules.orders.task_states import TaskStatus

NOW = datetime(2026, 10, 1, 14, 0, 0)


def make_task(task_id, status="open", due_in_minutes=30, priority="normal",
              completed_minutes_ago=None, worker_id=None) -> TaskRecord:
    order = OrderRecord(id=task_id, created_at=NOW, due_at=NOW + timedelta(minutes=due_in_minutes),
                        status="complete" if status == "picked" else "in_progress",
                        priority=priority)
    line = OrderLineRecord(id=task_id, sku_id="SKU-1", qty=1)
    order.lines.append(line)
    task = TaskRecord(id=task_id, sku_id="SKU-1", location_id="A1-01", qty=1, status=status)
    line.task = task
    if worker_id is not None or completed_minutes_ago is not None:
        completed_at = (NOW - timedelta(minutes=completed_minutes_ago)
                        if completed_minutes_ago is not None else None)
        task.assignments.append(AssignmentRecord(worker_id=worker_id or 1, assigned_at=NOW,
                                                 completed_at=completed_at))
    return task


def board_for(tasks):
    return build_live_board(tasks, [task.order for task in tasks], NOW)


def test_empty_board_has_every_column_and_zero_counts():
    board = build_live_board([], [], NOW)
    assert set(board.columns) == set(TaskStatus)
    assert board.summary.total_tasks == 0
    assert board.orders_by_status == {status: 0 for status in OrderStatus}


def test_tasks_land_in_their_status_column_with_their_worker():
    board = board_for([
        make_task(1, "open"),
        make_task(2, "assigned", worker_id=4),
        make_task(3, "exception", worker_id=5),
    ])
    assert [card.task_id for card in board.columns[TaskStatus.OPEN]] == [1]
    assert board.columns[TaskStatus.ASSIGNED][0].worker_id == 4
    assert board.summary.work_in_progress == 1
    assert board.summary.exceptions == 1


def test_expedited_orders_sort_before_earlier_due_normal_orders():
    board = board_for([
        make_task(1, due_in_minutes=10),
        make_task(2, due_in_minutes=50, priority="expedite"),
        make_task(3, due_in_minutes=5),
    ])
    assert [card.task_id for card in board.columns[TaskStatus.OPEN]] == [2, 3, 1]


def test_overdue_tasks_are_flagged_and_their_orders_counted_late():
    board = board_for([
        make_task(1, "open", due_in_minutes=-15),
        make_task(2, "assigned", due_in_minutes=20, worker_id=2),
    ])
    late_card = board.columns[TaskStatus.OPEN][0]
    assert late_card.is_late and late_card.minutes_until_due == -15
    assert not board.columns[TaskStatus.ASSIGNED][0].is_late
    assert board.summary.late_orders == 1
    assert board.orders_by_status[OrderStatus.LATE] == 1
    assert board.orders_by_status[OrderStatus.IN_PROGRESS] == 1


def test_picked_tasks_are_never_late():
    assert not is_late(make_task(1, "picked", due_in_minutes=-60, completed_minutes_ago=1), NOW)


def test_throughput_counts_only_picks_in_the_last_hour():
    board = board_for([
        make_task(1, "picked", completed_minutes_ago=5),
        make_task(2, "picked", completed_minutes_ago=59),
        make_task(3, "picked", completed_minutes_ago=61),
    ])
    assert board.summary.picked_last_hour == 2
    assert [card.task_id for card in board.columns[TaskStatus.PICKED]] == [1, 2]
    assert board.orders_by_status[OrderStatus.COMPLETE] == 3


def test_minutes_until_due_rounds_down():
    task = make_task(1, due_in_minutes=0)
    task.order.due_at = NOW + timedelta(seconds=90)
    assert minutes_until_due(task, NOW) == 1

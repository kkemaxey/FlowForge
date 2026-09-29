from datetime import datetime, timedelta

from app.modules.tasks.board import build_live_board, is_late, minutes_until_due
from app.modules.tasks.models import PickTaskRecord
from app.modules.tasks.task_states import TaskStatus

NOW = datetime(2026, 10, 1, 14, 0, 0)


def make_task(task_id, status="open", due_in_minutes=30, priority="normal",
              completed_minutes_ago=None, worker_id=None) -> PickTaskRecord:
    completed_at = (NOW - timedelta(minutes=completed_minutes_ago)
                    if completed_minutes_ago is not None else None)
    return PickTaskRecord(
        id=task_id, order_ref=f"ORD-{task_id}", sku="SKU-1", bin_location="A-01-1",
        quantity=1, priority=priority, status=status, assigned_worker_id=worker_id,
        due_at=NOW + timedelta(minutes=due_in_minutes), created_at=NOW, updated_at=NOW,
        completed_at=completed_at, exception_reason=None,
    )


def test_empty_board_has_every_column_and_zero_counts():
    board = build_live_board([], NOW)
    assert set(board.columns) == set(TaskStatus)
    assert board.summary.total_tasks == 0
    assert board.summary.work_in_progress == 0


def test_tasks_land_in_their_status_column():
    board = build_live_board([
        make_task(1, "open"),
        make_task(2, "assigned", worker_id=4),
        make_task(3, "in_progress", worker_id=5),
        make_task(4, "exception"),
    ], NOW)
    assert [card.id for card in board.columns[TaskStatus.OPEN]] == [1]
    assert [card.id for card in board.columns[TaskStatus.ASSIGNED]] == [2]
    assert [card.id for card in board.columns[TaskStatus.IN_PROGRESS]] == [3]
    assert board.summary.work_in_progress == 2
    assert board.summary.exceptions == 1


def test_expedited_tasks_sort_before_earlier_due_normal_tasks():
    board = build_live_board([
        make_task(1, due_in_minutes=10),
        make_task(2, due_in_minutes=50, priority="expedite"),
        make_task(3, due_in_minutes=5),
    ], NOW)
    assert [card.id for card in board.columns[TaskStatus.OPEN]] == [2, 3, 1]


def test_overdue_active_tasks_are_flagged_late():
    board = build_live_board([
        make_task(1, "open", due_in_minutes=-15),
        make_task(2, "in_progress", due_in_minutes=20),
    ], NOW)
    cards = {card.id: card for card in board.columns[TaskStatus.OPEN]
             + board.columns[TaskStatus.IN_PROGRESS]}
    assert cards[1].is_late and cards[1].minutes_until_due == -15
    assert not cards[2].is_late
    assert board.summary.late_tasks == 1


def test_picked_tasks_are_never_late():
    assert not is_late(make_task(1, "picked", due_in_minutes=-60, completed_minutes_ago=1),
                       NOW)


def test_throughput_counts_only_picks_in_the_last_hour():
    board = build_live_board([
        make_task(1, "picked", completed_minutes_ago=5),
        make_task(2, "picked", completed_minutes_ago=59),
        make_task(3, "picked", completed_minutes_ago=61),
    ], NOW)
    assert board.summary.picked_last_hour == 2
    assert [card.id for card in board.columns[TaskStatus.PICKED]] == [1, 2]


def test_minutes_until_due_rounds_down():
    task = make_task(1, due_in_minutes=0)
    task.due_at = NOW + timedelta(seconds=90)
    assert minutes_until_due(task, NOW) == 1

"""Builds the supervisor's live board from a list of tasks. Pure logic, no I/O."""
from collections.abc import Iterable
from datetime import datetime, timedelta

from app.modules.tasks.models import PickTaskRecord
from app.modules.tasks.schema import BoardCard, BoardSummary, LiveBoard
from app.modules.tasks.task_states import (ACTIVE_STATUSES, WIP_STATUSES, TaskPriority,
                                           TaskStatus)

THROUGHPUT_WINDOW = timedelta(hours=1)


def is_late(task: PickTaskRecord, now: datetime) -> bool:
    return TaskStatus(task.status) in ACTIVE_STATUSES and task.due_at < now


def minutes_until_due(task: PickTaskRecord, now: datetime) -> int:
    """Whole minutes until the due time; negative once the task is overdue."""
    return int((task.due_at - now).total_seconds() // 60)


def card_sort_key(task: PickTaskRecord) -> tuple:
    # Expedited work floats to the top, then the soonest deadline.
    return (task.priority != TaskPriority.EXPEDITE, task.due_at, task.id)


def to_card(task: PickTaskRecord, now: datetime) -> BoardCard:
    return BoardCard(
        id=task.id,
        order_ref=task.order_ref,
        sku=task.sku,
        bin_location=task.bin_location,
        quantity=task.quantity,
        priority=TaskPriority(task.priority),
        assigned_worker_id=task.assigned_worker_id,
        due_at=task.due_at,
        minutes_until_due=minutes_until_due(task, now),
        is_late=is_late(task, now),
    )


def picked_within_window(task: PickTaskRecord, now: datetime) -> bool:
    return (task.status == TaskStatus.PICKED
            and task.completed_at is not None
            and task.completed_at >= now - THROUGHPUT_WINDOW)


def build_live_board(tasks: Iterable[PickTaskRecord], now: datetime) -> LiveBoard:
    columns: dict[TaskStatus, list[PickTaskRecord]] = {status: [] for status in TaskStatus}
    for task in tasks:
        status = TaskStatus(task.status)
        # Finished work only stays on the board for the throughput window.
        if status == TaskStatus.PICKED and not picked_within_window(task, now):
            continue
        columns[status].append(task)

    visible_tasks = [task for column in columns.values() for task in column]
    summary = BoardSummary(
        total_tasks=len(visible_tasks),
        work_in_progress=sum(len(columns[status]) for status in WIP_STATUSES),
        late_tasks=sum(1 for task in visible_tasks if is_late(task, now)),
        exceptions=len(columns[TaskStatus.EXCEPTION]),
        picked_last_hour=len(columns[TaskStatus.PICKED]),
    )
    return LiveBoard(
        generated_at=now,
        summary=summary,
        columns={
            status: [to_card(task, now) for task in sorted(column, key=card_sort_key)]
            for status, column in columns.items()
        },
    )

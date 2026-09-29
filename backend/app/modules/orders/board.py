"""Builds the supervisor's live board from tasks and orders. Pure logic, no I/O."""
from collections.abc import Iterable
from datetime import datetime, timedelta

from app.modules.orders.models import OrderRecord, TaskRecord
from app.modules.orders.order_status import OrderPriority, OrderStatus, effective_status
from app.modules.orders.schema import BoardCard, BoardSummary, LiveBoard
from app.modules.orders.task_states import WIP_STATUSES, TaskStatus

THROUGHPUT_WINDOW = timedelta(hours=1)


def is_late(task: TaskRecord, now: datetime) -> bool:
    return task.status != TaskStatus.PICKED and task.order.due_at < now


def minutes_until_due(task: TaskRecord, now: datetime) -> int:
    """Whole minutes until the order is due; negative once it is overdue."""
    return int((task.order.due_at - now).total_seconds() // 60)


def card_sort_key(task: TaskRecord) -> tuple:
    # Expedited orders float to the top, then the soonest deadline.
    return (task.order.priority != OrderPriority.EXPEDITE, task.order.due_at, task.id)


def picked_within_window(task: TaskRecord, now: datetime) -> bool:
    assignment = task.current_assignment
    return (task.status == TaskStatus.PICKED
            and assignment is not None
            and assignment.completed_at is not None
            and assignment.completed_at >= now - THROUGHPUT_WINDOW)


def to_card(task: TaskRecord, now: datetime) -> BoardCard:
    assignment = task.current_assignment
    return BoardCard(
        task_id=task.id,
        order_id=task.order.id,
        sku_id=task.sku_id,
        location_id=task.location_id,
        qty=task.qty,
        priority=OrderPriority(task.order.priority),
        worker_id=assignment.worker_id if assignment else None,
        due_at=task.order.due_at,
        minutes_until_due=minutes_until_due(task, now),
        is_late=is_late(task, now),
    )


def count_orders_by_status(orders: Iterable[OrderRecord], now: datetime) -> dict[OrderStatus, int]:
    counts = {status: 0 for status in OrderStatus}
    for order in orders:
        counts[effective_status(order.status, order.due_at, now)] += 1
    return counts


def build_live_board(tasks: Iterable[TaskRecord], orders: Iterable[OrderRecord],
                     now: datetime) -> LiveBoard:
    columns: dict[TaskStatus, list[TaskRecord]] = {status: [] for status in TaskStatus}
    for task in tasks:
        status = TaskStatus(task.status)
        # Finished work only stays on the board for the throughput window.
        if status == TaskStatus.PICKED and not picked_within_window(task, now):
            continue
        columns[status].append(task)

    orders_by_status = count_orders_by_status(orders, now)
    summary = BoardSummary(
        total_tasks=sum(len(column) for column in columns.values()),
        work_in_progress=sum(len(columns[status]) for status in WIP_STATUSES),
        exceptions=len(columns[TaskStatus.EXCEPTION]),
        late_orders=orders_by_status[OrderStatus.LATE],
        picked_last_hour=len(columns[TaskStatus.PICKED]),
    )
    return LiveBoard(
        generated_at=now,
        summary=summary,
        orders_by_status=orders_by_status,
        columns={
            status: [to_card(task, now) for task in sorted(column, key=card_sort_key)]
            for status, column in columns.items()
        },
    )

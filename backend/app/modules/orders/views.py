"""Turns database records into API views."""
from datetime import datetime

from app.modules.orders.models import OrderRecord, TaskRecord
from app.modules.orders.order_status import OrderPriority, effective_status
from app.modules.orders.schema import OrderView, TaskView
from app.modules.orders.task_states import TaskStatus


def task_view(task: TaskRecord) -> TaskView:
    assignment = task.current_assignment
    return TaskView(
        id=task.id,
        order_id=task.order.id,
        order_line_id=task.order_line.id,
        sku_id=task.sku_id,
        location_id=task.location_id,
        qty=task.qty,
        status=TaskStatus(task.status),
        worker_id=assignment.worker_id if assignment else None,
        assigned_at=assignment.assigned_at if assignment else None,
        completed_at=assignment.completed_at if assignment else None,
    )


def order_view(order: OrderRecord, now: datetime) -> OrderView:
    return OrderView(
        id=order.id,
        status=effective_status(order.status, order.due_at, now),
        priority=OrderPriority(order.priority),
        created_at=order.created_at,
        due_at=order.due_at,
        tasks=[task_view(line.task) for line in order.lines],
    )

"""Business rules: order intake, task generation, the task lifecycle and the live board."""
import logging
from collections.abc import Callable
from datetime import datetime

from app.core.clock import to_naive_utc, utc_now
from app.core.errors import NotFoundError, ValidationFailedError
from app.modules.orders.board import THROUGHPUT_WINDOW, build_live_board
from app.modules.orders.models import AssignmentRecord, OrderLineRecord, OrderRecord, TaskRecord
from app.modules.orders.order_status import OrderPriority, OrderStatus, progress_status
from app.modules.orders.repository import OrderRepository
from app.modules.orders.schema import (LiveBoard, OrderCreate, OrderView, TaskStatusUpdate,
                                       TaskView)
from app.modules.orders.task_states import TaskStatus, ensure_transition
from app.modules.orders.views import order_view, task_view

logger = logging.getLogger("flowforge.orders")


class OrderService:
    def __init__(self, repository: OrderRepository, clock: Callable[[], datetime] = utc_now):
        self._repository = repository
        self._clock = clock

    def create_order(self, request: OrderCreate) -> OrderView:
        """Saves the order and generates one open pick task per order line."""
        now = self._clock()
        due_at = to_naive_utc(request.due_at)
        if due_at <= now:
            raise ValidationFailedError("due_at must be in the future.")

        order = OrderRecord(created_at=now, due_at=due_at, status=OrderStatus.NEW.value,
                            priority=request.priority.value)
        for line_request in request.lines:
            line = OrderLineRecord(sku_id=line_request.sku_id, qty=line_request.qty)
            line.task = TaskRecord(sku_id=line_request.sku_id, qty=line_request.qty,
                                   location_id=line_request.location_id,
                                   status=TaskStatus.OPEN.value)
            order.lines.append(line)

        self._repository.add_order(order)
        logger.info("order created id=%s lines=%d priority=%s",
                    order.id, len(order.lines), order.priority)
        return order_view(order, now)

    def get_order(self, order_id: int) -> OrderView:
        return order_view(self._find_order(order_id), self._clock())

    def expedite_order(self, order_id: int) -> OrderView:
        order = self._find_order(order_id)
        if order.status == OrderStatus.COMPLETE:
            raise ValidationFailedError("A complete order cannot be expedited.")
        order.priority = OrderPriority.EXPEDITE.value
        self._repository.save()
        logger.info("order expedited id=%s", order.id)
        return order_view(order, self._clock())

    def get_task(self, task_id: int) -> TaskView:
        return task_view(self._find_task(task_id))

    def list_tasks(self, status: TaskStatus | None = None) -> list[TaskView]:
        return [task_view(task) for task in self._repository.list_tasks(status)]

    def change_task_status(self, task_id: int, update: TaskStatusUpdate) -> TaskView:
        task = self._find_task(task_id)
        current_status = TaskStatus(task.status)
        target_status = update.status
        ensure_transition(current_status, target_status)
        now = self._clock()

        if target_status == TaskStatus.ASSIGNED:
            if update.worker_id is None:
                raise ValidationFailedError("worker_id is required to assign a task.")
            task.assignments.append(
                AssignmentRecord(worker_id=update.worker_id, assigned_at=now))
        elif target_status == TaskStatus.PICKED:
            task.current_assignment.completed_at = now
        elif target_status == TaskStatus.OPEN:
            # Back to the pool: the unfinished assignment is dropped.
            task.assignments.remove(task.current_assignment)

        task.status = target_status.value
        task.order.status = progress_status(line.task.status for line in task.order.lines).value
        self._repository.save()
        logger.info("task status changed id=%s from=%s to=%s order_id=%s order_status=%s",
                    task.id, current_status, target_status, task.order.id, task.order.status)
        return task_view(task)

    def live_board(self) -> LiveBoard:
        now = self._clock()
        tasks = self._repository.list_board_tasks(picked_since=now - THROUGHPUT_WINDOW)
        return build_live_board(tasks, self._repository.list_orders(), now)

    def _find_order(self, order_id: int) -> OrderRecord:
        order = self._repository.get_order(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} does not exist.")
        return order

    def _find_task(self, task_id: int) -> TaskRecord:
        task = self._repository.get_task(task_id)
        if task is None:
            raise NotFoundError(f"Task {task_id} does not exist.")
        return task

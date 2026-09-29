"""In-memory stand-ins so business logic can be tested without a database."""
from datetime import datetime

from app.modules.orders.models import OrderRecord, TaskRecord
from app.modules.orders.task_states import TaskStatus


class FakeOrderRepository:
    def __init__(self):
        self.orders: dict[int, OrderRecord] = {}
        self.tasks: dict[int, TaskRecord] = {}
        self._next_line_id = 1
        self.save_count = 0

    def add_order(self, order: OrderRecord) -> OrderRecord:
        order.id = len(self.orders) + 1
        self.orders[order.id] = order
        for line in order.lines:
            line.id = self._next_line_id
            line.task.id = self._next_line_id
            self._next_line_id += 1
            self.tasks[line.task.id] = line.task
        return order

    def get_order(self, order_id: int) -> OrderRecord | None:
        return self.orders.get(order_id)

    def list_orders(self) -> list[OrderRecord]:
        return list(self.orders.values())

    def get_task(self, task_id: int) -> TaskRecord | None:
        return self.tasks.get(task_id)

    def list_tasks(self, status: TaskStatus | None = None) -> list[TaskRecord]:
        return [task for task in self.tasks.values() if status is None or task.status == status]

    def list_board_tasks(self, picked_since: datetime) -> list[TaskRecord]:
        return [task for task in self.tasks.values()
                if task.status != TaskStatus.PICKED
                or task.current_assignment.completed_at >= picked_since]

    def save(self) -> None:
        self.save_count += 1


class FixedClock:
    """A clock the test can move forward by hand."""

    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now

"""Data access for orders and tasks. All queries go through the ORM with bound parameters."""
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.modules.orders.models import AssignmentRecord, OrderLineRecord, OrderRecord, TaskRecord
from app.modules.orders.task_states import TaskStatus

# Load a task's order and assignments in the same round trip as the task.
TASK_DETAILS = (
    selectinload(TaskRecord.order_line).selectinload(OrderLineRecord.order),
    selectinload(TaskRecord.assignments),
)


class OrderRepository:
    def __init__(self, session: Session):
        self._session = session

    def add_order(self, order: OrderRecord) -> OrderRecord:
        self._session.add(order)
        self._session.flush()  # assigns ids to the order, its lines and tasks
        return order

    def get_order(self, order_id: int) -> OrderRecord | None:
        return self._session.get(OrderRecord, order_id)

    def list_orders(self) -> list[OrderRecord]:
        return list(self._session.scalars(select(OrderRecord)))

    def get_task(self, task_id: int) -> TaskRecord | None:
        return self._session.get(TaskRecord, task_id, options=TASK_DETAILS)

    def list_tasks(self, status: TaskStatus | None = None) -> list[TaskRecord]:
        query = select(TaskRecord).options(*TASK_DETAILS).order_by(TaskRecord.id)
        if status is not None:
            query = query.where(TaskRecord.status == status.value)
        return list(self._session.scalars(query))

    def list_board_tasks(self, picked_since: datetime) -> list[TaskRecord]:
        """Every unfinished task, plus tasks picked since the given time."""
        recently_picked = select(AssignmentRecord.task_id).where(
            AssignmentRecord.completed_at >= picked_since)
        query = select(TaskRecord).options(*TASK_DETAILS).where(
            or_(TaskRecord.status != TaskStatus.PICKED.value,
                TaskRecord.id.in_(recently_picked)))
        return list(self._session.scalars(query))

    def save(self) -> None:
        self._session.flush()

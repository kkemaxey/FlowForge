"""Data access for pick tasks. All queries go through the ORM with bound parameters."""
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.modules.tasks.models import PickTaskRecord
from app.modules.tasks.task_states import TaskStatus


class TaskRepository:
    def __init__(self, session: Session):
        self._session = session

    def add(self, task: PickTaskRecord) -> PickTaskRecord:
        self._session.add(task)
        self._session.flush()  # assigns the id
        return task

    def get(self, task_id: int) -> PickTaskRecord | None:
        return self._session.get(PickTaskRecord, task_id)

    def save(self, task: PickTaskRecord) -> PickTaskRecord:
        self._session.flush()
        return task

    def list(self, status: TaskStatus | None = None) -> list[PickTaskRecord]:
        query = select(PickTaskRecord).order_by(PickTaskRecord.due_at, PickTaskRecord.id)
        if status is not None:
            query = query.where(PickTaskRecord.status == status.value)
        return list(self._session.scalars(query))

    def list_for_board(self, picked_since: datetime) -> list[PickTaskRecord]:
        """Every unfinished task, plus tasks picked since the given time."""
        query = select(PickTaskRecord).where(
            or_(
                PickTaskRecord.status != TaskStatus.PICKED.value,
                PickTaskRecord.completed_at >= picked_since,
            )
        )
        return list(self._session.scalars(query))

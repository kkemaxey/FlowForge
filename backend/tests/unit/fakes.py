"""In-memory stand-ins so business logic can be tested without a database."""
from datetime import datetime

from app.modules.tasks.models import PickTaskRecord
from app.modules.tasks.task_states import TaskStatus


class FakeTaskRepository:
    def __init__(self):
        self.tasks: dict[int, PickTaskRecord] = {}
        self._next_id = 1

    def add(self, task: PickTaskRecord) -> PickTaskRecord:
        task.id = self._next_id
        self._next_id += 1
        self.tasks[task.id] = task
        return task

    def get(self, task_id: int) -> PickTaskRecord | None:
        return self.tasks.get(task_id)

    def save(self, task: PickTaskRecord) -> PickTaskRecord:
        return task

    def list(self, status: TaskStatus | None = None) -> list[PickTaskRecord]:
        matching = [t for t in self.tasks.values() if status is None or t.status == status]
        return sorted(matching, key=lambda t: (t.due_at, t.id))

    def list_for_board(self, picked_since: datetime) -> list[PickTaskRecord]:
        return [t for t in self.tasks.values()
                if t.status != TaskStatus.PICKED or t.completed_at >= picked_since]


class FixedClock:
    """A clock the test can move forward by hand."""

    def __init__(self, now: datetime):
        self.now = now

    def __call__(self) -> datetime:
        return self.now

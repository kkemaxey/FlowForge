"""Business rules for creating pick tasks and moving them through their lifecycle."""
import logging
from collections.abc import Callable
from datetime import datetime

from app.core.clock import to_naive_utc, utc_now
from app.core.errors import NotFoundError, ValidationFailedError
from app.modules.tasks.board import THROUGHPUT_WINDOW, build_live_board
from app.modules.tasks.models import PickTaskRecord
from app.modules.tasks.repository import TaskRepository
from app.modules.tasks.schema import LiveBoard, TaskCreate, TaskStatusUpdate
from app.modules.tasks.task_states import TaskPriority, TaskStatus, ensure_transition

logger = logging.getLogger("flowforge.tasks")


class TaskService:
    def __init__(self, repository: TaskRepository, clock: Callable[[], datetime] = utc_now):
        self._repository = repository
        self._clock = clock

    def create_task(self, request: TaskCreate) -> PickTaskRecord:
        now = self._clock()
        due_at = to_naive_utc(request.due_at)
        if due_at <= now:
            raise ValidationFailedError("due_at must be in the future.")

        task = PickTaskRecord(
            order_ref=request.order_ref.strip(),
            sku=request.sku.strip().upper(),
            bin_location=request.bin_location,
            quantity=request.quantity,
            priority=request.priority.value,
            status=TaskStatus.OPEN.value,
            assigned_worker_id=None,
            due_at=due_at,
            created_at=now,
            updated_at=now,
            completed_at=None,
            exception_reason=None,
        )
        self._repository.add(task)
        logger.info("task created id=%s order_ref=%s priority=%s",
                    task.id, task.order_ref, task.priority)
        return task

    def get_task(self, task_id: int) -> PickTaskRecord:
        task = self._repository.get(task_id)
        if task is None:
            raise NotFoundError(f"Task {task_id} does not exist.")
        return task

    def list_tasks(self, status: TaskStatus | None = None) -> list[PickTaskRecord]:
        return self._repository.list(status)

    def change_status(self, task_id: int, update: TaskStatusUpdate) -> PickTaskRecord:
        task = self.get_task(task_id)
        current_status = TaskStatus(task.status)
        target_status = update.status
        ensure_transition(current_status, target_status)

        if target_status == TaskStatus.ASSIGNED:
            if update.worker_id is None:
                raise ValidationFailedError("worker_id is required to assign a task.")
            task.assigned_worker_id = update.worker_id
        elif target_status == TaskStatus.EXCEPTION:
            if not update.reason or not update.reason.strip():
                raise ValidationFailedError("reason is required to raise an exception.")
            task.exception_reason = update.reason.strip()
        elif target_status == TaskStatus.OPEN:
            # Back to the pool: nobody owns it and any exception is resolved.
            task.assigned_worker_id = None
            task.exception_reason = None
        elif target_status == TaskStatus.PICKED:
            task.completed_at = self._clock()

        task.status = target_status.value
        task.updated_at = self._clock()
        self._repository.save(task)
        logger.info("task status changed id=%s from=%s to=%s worker_id=%s",
                    task.id, current_status, target_status, task.assigned_worker_id)
        return task

    def expedite(self, task_id: int) -> PickTaskRecord:
        task = self.get_task(task_id)
        if task.status == TaskStatus.PICKED:
            raise ValidationFailedError("A picked task cannot be expedited.")
        task.priority = TaskPriority.EXPEDITE.value
        task.updated_at = self._clock()
        self._repository.save(task)
        logger.info("task expedited id=%s", task.id)
        return task

    def live_board(self) -> LiveBoard:
        now = self._clock()
        tasks = self._repository.list_for_board(picked_since=now - THROUGHPUT_WINDOW)
        return build_live_board(tasks, now)

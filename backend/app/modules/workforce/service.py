"""Business rules for adding workers and listing the workforce."""
import logging

from app.core.errors import ConflictError, ValidationFailedError
from app.modules.workforce.models import WorkerRecord
from app.modules.workforce.repository import WorkerRepository
from app.modules.workforce.schema import (WorkerCreate, WorkerStatus, WorkerType,
                                          WorkerView)

logger = logging.getLogger("flowforge.workforce")

# Fastest believable speed for each kind of worker, in grid cells per second.
MAX_SPEED = {WorkerType.HUMAN: 2.0, WorkerType.ROBOT: 4.0}


class WorkerService:
    def __init__(self, repository: WorkerRepository):
        self._repository = repository

    def create_worker(self, request: WorkerCreate) -> WorkerView:
        max_speed = MAX_SPEED[request.type]
        if request.speed > max_speed:
            raise ValidationFailedError(
                f"speed for a {request.type} worker can be at most {max_speed}.")
        if request.status == WorkerStatus.BUSY and not request.enabled:
            raise ValidationFailedError("A disabled worker cannot be busy.")
        if self._repository.find_by_name(request.name) is not None:
            raise ConflictError(f"A worker named '{request.name}' already exists.")

        worker = WorkerRecord(**request.model_dump(mode="json"))
        self._repository.add_worker(worker)
        logger.info("worker created id=%s type=%s at=(%d,%d)",
                    worker.id, worker.type, worker.cur_x, worker.cur_y)
        return WorkerView.model_validate(worker)

    def list_workers(self, worker_type: WorkerType | None = None,
                     status: WorkerStatus | None = None) -> list[WorkerView]:
        return [WorkerView.model_validate(worker)
                for worker in self._repository.list_workers(worker_type, status)]

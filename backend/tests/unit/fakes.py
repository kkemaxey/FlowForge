"""In-memory stand-in so business logic can be tested without a database."""
from app.modules.workforce.models import WorkerRecord
from app.modules.workforce.schema import WorkerStatus, WorkerType


class FakeWorkerRepository:
    def __init__(self):
        self.workers: dict[int, WorkerRecord] = {}

    def add_worker(self, worker: WorkerRecord) -> WorkerRecord:
        worker.id = len(self.workers) + 1
        self.workers[worker.id] = worker
        return worker

    def find_by_name(self, name: str) -> WorkerRecord | None:
        return next((worker for worker in self.workers.values()
                     if worker.name.lower() == name.lower()), None)

    def list_workers(self, worker_type: WorkerType | None = None,
                     status: WorkerStatus | None = None) -> list[WorkerRecord]:
        return [worker for worker in sorted(self.workers.values(), key=lambda w: w.id)
                if (worker_type is None or worker.type == worker_type)
                and (status is None or worker.status == status)]

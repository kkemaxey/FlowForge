"""Data access for workers. All queries go through the ORM with bound parameters."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.workforce.models import WorkerRecord
from app.modules.workforce.schema import WorkerStatus, WorkerType


class WorkerRepository:
    def __init__(self, session: Session):
        self._session = session

    def add_worker(self, worker: WorkerRecord) -> WorkerRecord:
        self._session.add(worker)
        self._session.flush()  # assigns the id
        return worker

    def find_by_name(self, name: str) -> WorkerRecord | None:
        query = select(WorkerRecord).where(func.lower(WorkerRecord.name) == name.lower())
        return self._session.scalars(query).first()

    def list_workers(self, worker_type: WorkerType | None = None,
                     status: WorkerStatus | None = None) -> list[WorkerRecord]:
        query = select(WorkerRecord).order_by(WorkerRecord.id)
        if worker_type is not None:
            query = query.where(WorkerRecord.type == worker_type.value)
        if status is not None:
            query = query.where(WorkerRecord.status == status.value)
        return list(self._session.scalars(query))

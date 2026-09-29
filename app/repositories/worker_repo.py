from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import WorkerRow
from app.services.workforce import Worker


def _to_worker(row: WorkerRow) -> Worker:
    return Worker(id=row.id, name=row.name, type=row.type, speed=row.speed,
                  cur_x=row.cur_x, cur_y=row.cur_y, status=row.status, enabled=row.enabled)


class SqlWorkerRepository:
    def __init__(self, session: Session):
        self._session = session

    def list_workers(self, status: Optional[str] = None, worker_type: Optional[str] = None) -> List[Worker]:
        statement = select(WorkerRow).order_by(WorkerRow.id)
        if status is not None:
            statement = statement.where(WorkerRow.status == status)
        if worker_type is not None:
            statement = statement.where(WorkerRow.type == worker_type)
        return [_to_worker(row) for row in self._session.scalars(statement)]

    def get(self, worker_id: int) -> Optional[Worker]:
        row = self._session.get(WorkerRow, worker_id)
        return _to_worker(row) if row is not None else None

    def add(self, name: str, worker_type: str, speed: float, cur_x: int, cur_y: int,
            status: str, enabled: bool) -> Worker:
        row = WorkerRow(name=name, type=worker_type, speed=speed, cur_x=cur_x, cur_y=cur_y,
                        status=status, enabled=enabled)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _to_worker(row)

    def update(self, worker_id: int, changes: Dict[str, Any]) -> Worker:
        row = self._session.get(WorkerRow, worker_id)
        for field_name, value in changes.items():
            setattr(row, field_name, value)
        self._session.commit()
        self._session.refresh(row)
        return _to_worker(row)

    def delete(self, worker_id: int) -> None:
        row = self._session.get(WorkerRow, worker_id)
        if row is not None:
            self._session.delete(row)
            self._session.commit()

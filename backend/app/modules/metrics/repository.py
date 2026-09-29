from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.metrics.models import EventRow
from app.modules.metrics.service import EventRecord


def _to_event(row: EventRow) -> EventRecord:
    return EventRecord(id=row.id, ts=row.ts, type=row.type, task_id=row.task_id,
                       worker_id=row.worker_id, qty=row.qty, payload=row.payload)


class SqlEventRepository:
    def __init__(self, session: Session):
        self._session = session

    def add(self, event_type: str, ts: datetime, task_id: Optional[int], worker_id: Optional[int],
            qty: Optional[int], payload: Optional[Dict[str, Any]]) -> EventRecord:
        row = EventRow(type=event_type, ts=ts, task_id=task_id, worker_id=worker_id,
                       qty=qty, payload=payload)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return _to_event(row)

    def list_since(self, cutoff: datetime) -> List[EventRecord]:
        statement = (select(EventRow).where(EventRow.ts >= cutoff)
                     .order_by(EventRow.ts, EventRow.id))
        return [_to_event(row) for row in self._session.scalars(statement)]

    def list_task_events(self) -> List[EventRecord]:
        statement = (select(EventRow).where(EventRow.task_id.is_not(None))
                     .order_by(EventRow.ts, EventRow.id))
        return [_to_event(row) for row in self._session.scalars(statement)]

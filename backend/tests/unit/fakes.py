"""In-memory repositories so service tests never touch a database."""
import dataclasses
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

from app.modules.metrics.service import EventRecord
from app.modules.workforce.service import Worker


def make_worker(**overrides: Any) -> Worker:
    fields: Dict[str, Any] = dict(
        id=1, name="Picker", type="human", speed=1.0,
        cur_x=0, cur_y=0, status="idle", enabled=True,
    )
    fields.update(overrides)
    return Worker(**fields)


class FakeWorkerRepository:
    def __init__(self, workers: Iterable[Worker] = ()):
        self._workers: Dict[int, Worker] = {}
        self._next_id = 1
        for worker in workers:
            self._workers[worker.id] = worker
            self._next_id = max(self._next_id, worker.id + 1)

    def list_workers(self, status: Optional[str] = None, worker_type: Optional[str] = None) -> List[Worker]:
        return [
            worker
            for worker in sorted(self._workers.values(), key=lambda w: w.id)
            if (status is None or worker.status == status)
            and (worker_type is None or worker.type == worker_type)
        ]

    def get(self, worker_id: int) -> Optional[Worker]:
        return self._workers.get(worker_id)

    def add(self, name: str, worker_type: str, speed: float, cur_x: int, cur_y: int,
            status: str, enabled: bool) -> Worker:
        worker = Worker(id=self._next_id, name=name, type=worker_type, speed=speed,
                        cur_x=cur_x, cur_y=cur_y, status=status, enabled=enabled)
        self._workers[worker.id] = worker
        self._next_id += 1
        return worker

    def update(self, worker_id: int, changes: Dict[str, Any]) -> Worker:
        updated = dataclasses.replace(self._workers[worker_id], **changes)
        self._workers[worker_id] = updated
        return updated

    def delete(self, worker_id: int) -> None:
        del self._workers[worker_id]


class FakeEventRepository:
    def __init__(self):
        self.events: List[EventRecord] = []

    def add(self, event_type: str, ts: datetime, task_id: Optional[int], worker_id: Optional[int],
            qty: Optional[int], payload: Optional[Dict[str, Any]]) -> EventRecord:
        event = EventRecord(id=len(self.events) + 1, ts=ts, type=event_type, task_id=task_id,
                            worker_id=worker_id, qty=qty, payload=payload)
        self.events.append(event)
        return event

    def list_since(self, cutoff: datetime) -> List[EventRecord]:
        return [event for event in self.events if event.ts >= cutoff]

    def list_task_events(self) -> List[EventRecord]:
        return [event for event in self.events if event.task_id is not None]

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Worker

DEFAULT_WORKERS = (
    {
        "name": "Worker 1",
        "worker_type": "human",
        "speed": 2,
        "cur_x": 3,
        "cur_y": 2,
        "status": "idle",
        "enabled": True,
    },
    {
        "name": "Robot 1",
        "worker_type": "robot",
        "speed": 4,
        "cur_x": 15,
        "cur_y": 9,
        "status": "idle",
        "enabled": True,
    },
)


def serialize_worker(worker: Worker) -> dict[str, object]:
    return {
        "id": worker.id,
        "name": worker.name,
        "type": worker.type,
        "speed": worker.speed,
        "cur_x": worker.cur_x,
        "cur_y": worker.cur_y,
        "status": worker.status,
        "enabled": worker.enabled,
    }


def list_workers(session: Session) -> list[dict[str, object]]:
    workers = session.scalars(select(Worker).order_by(Worker.id)).all()
    if not workers:
        session.add_all(Worker(**worker_data) for worker_data in DEFAULT_WORKERS)
        session.commit()
        workers = session.scalars(select(Worker).order_by(Worker.id)).all()

    return [serialize_worker(worker) for worker in workers]


def create_worker(session: Session, worker_data: dict[str, object]) -> dict[str, object]:
    worker = Worker(**worker_data)
    session.add(worker)
    session.commit()
    session.refresh(worker)
    return serialize_worker(worker)
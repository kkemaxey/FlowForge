from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.simulation import service
from app.modules.simulation.schemas import (
    ExceptionCreate,
    ExceptionListOut,
    ExceptionOut,
    PickCreate,
    PickOut,
    WorkerRecoveredOut,
)

router = APIRouter(prefix="/api/v1", tags=["simulation"])


@router.post("/tasks/{task_id}/pick", response_model=PickOut)
def pick_task(task_id: int, payload: PickCreate, db: Session = Depends(get_db)) -> PickOut:
    """A worker finished picking: remove the stock, free the worker, and complete the order if done."""
    return service.pick_task(db, task_id, payload.assignment_id)


@router.post("/tasks/{task_id}/exceptions", response_model=ExceptionOut, status_code=201)
def create_exception(task_id: int, payload: ExceptionCreate, db: Session = Depends(get_db)) -> ExceptionOut:
    """A stockout, jam or worker going down interrupted an assignment: record it and recover the task."""
    return service.open_exception(db, task_id, payload)


@router.get("/exceptions", response_model=ExceptionListOut)
def list_exceptions(
    only_open: bool | None = Query(
        default=None, alias="open", description="true: unresolved only; false: resolved only; omit: all"
    ),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> ExceptionListOut:
    """Exceptions, newest first."""
    return service.list_exceptions(db, only_open, limit)


@router.post("/simulation/workers/{worker_id}/recover", response_model=WorkerRecoveredOut)
def recover_worker(worker_id: int, db: Session = Depends(get_db)) -> WorkerRecoveredOut:
    """Bring a worker that went down back to idle, so the assigner can use them again."""
    return service.recover_worker(db, worker_id)

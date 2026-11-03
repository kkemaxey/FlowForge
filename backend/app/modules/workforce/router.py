from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.workforce import service
from app.modules.workforce.models import WorkerKind, WorkerStatus
from app.modules.workforce.schemas import WorkerCreate, WorkerListOut, WorkerOut, WorkerUpdate

router = APIRouter(prefix="/api/v1/workers", tags=["workforce"])


@router.get("", response_model=WorkerListOut)
def list_workers(
    status: WorkerStatus | None = Query(default=None),
    kind: WorkerKind | None = Query(default=None),
    include_inactive: bool = Query(default=False, description="Also list deactivated workers"),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> WorkerListOut:
    """Workers by id. Deactivated workers are hidden unless include_inactive=true."""
    return service.list_workers(db, status, kind, include_inactive, limit)


@router.get("/{worker_id}", response_model=WorkerOut)
def get_worker(worker_id: int, db: Session = Depends(get_db)) -> WorkerOut:
    return WorkerOut.of(service.get_worker(db, worker_id))


@router.post("", response_model=WorkerOut, status_code=status.HTTP_201_CREATED)
def create_worker(payload: WorkerCreate, response: Response, db: Session = Depends(get_db)) -> WorkerOut:
    worker = service.create_worker(db, payload)
    response.headers["Location"] = f"{router.prefix}/{worker.id}"
    return WorkerOut.of(worker)


@router.patch("/{worker_id}", response_model=WorkerOut)
def update_worker(worker_id: int, payload: WorkerUpdate, db: Session = Depends(get_db)) -> WorkerOut:
    """Edit name, kind, position or speed. expected_version must match (409 version_conflict)."""
    return WorkerOut.of(service.update_worker(db, worker_id, payload))


@router.delete("/{worker_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_worker(worker_id: int, db: Session = Depends(get_db)) -> Response:
    """Soft delete: is_active=false, status=offline. The row stays for assignment history."""
    service.deactivate_worker(db, worker_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

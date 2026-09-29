"""HTTP endpoints for the workforce: add a worker, list workers."""
from collections.abc import Iterator

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.errors import error_body
from app.modules.workforce.repository import WorkerRepository
from app.modules.workforce.schema import WorkerCreate, WorkerStatus, WorkerType, WorkerView
from app.modules.workforce.service import WorkerService

router = APIRouter(prefix="/api", tags=["workers"])


def get_worker_service(request: Request) -> Iterator[WorkerService]:
    database = request.app.state.database
    for session in database.session():
        yield WorkerService(WorkerRepository(session))


def error_example(description: str, code: str, message: str) -> dict:
    return {"description": description,
            "content": {"application/json": {"example": error_body(code, message)}}}


@router.post("/workers", response_model=WorkerView, status_code=status.HTTP_201_CREATED,
             summary="Add a worker",
             responses={409: error_example("Name already taken", "conflict",
                                           "A worker named 'Maria Lopez' already exists."),
                        422: error_example("Invalid input", "validation_failed",
                                           "speed for a human worker can be at most 2.0.")})
def create_worker(body: WorkerCreate, service: WorkerService = Depends(get_worker_service)):
    """Saves a human or robot worker. New workers start `idle` at the dock (0, 0) unless a
    position is given."""
    return service.create_worker(body)


@router.get("/workers", response_model=list[WorkerView], summary="List workers")
def list_workers(worker_type: WorkerType | None = Query(default=None, alias="type"),
                 status_filter: WorkerStatus | None = Query(default=None, alias="status"),
                 service: WorkerService = Depends(get_worker_service)):
    """Every worker in the order they were added. Filter with `?type=robot` or `?status=idle`."""
    return service.list_workers(worker_type, status_filter)

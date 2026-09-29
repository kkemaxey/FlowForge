from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response

from app.dependencies import get_workforce_service
from app.schemas import ErrorResponse, WorkerCreate, WorkerOut, WorkerStatus, WorkerType, WorkerUpdate
from app.services.workforce import Worker, WorkforceService

router = APIRouter(prefix="/api/workers", tags=["workers"])

NOT_FOUND = {404: {"model": ErrorResponse, "description": "Worker does not exist"}}
INVALID = {422: {"model": ErrorResponse, "description": "Validation or business-rule failure"}}


@router.get("", response_model=List[WorkerOut], responses=INVALID,
            summary="List workers and robots",
            description="Optionally filter by `status` (idle, busy) and/or `type` (human, robot).")
def list_workers(
    status: Optional[WorkerStatus] = None,
    worker_type: Optional[WorkerType] = Query(default=None, alias="type"),
    service: WorkforceService = Depends(get_workforce_service),
) -> List[Worker]:
    return service.list_workers(status=status, worker_type=worker_type)


@router.get("/{worker_id}", response_model=WorkerOut, responses=NOT_FOUND,
            summary="Get one worker")
def get_worker(worker_id: int, service: WorkforceService = Depends(get_workforce_service)) -> Worker:
    return service.get_worker(worker_id)


@router.post("", response_model=WorkerOut, status_code=201, responses=INVALID,
             summary="Create a worker or robot",
             description="New workers start `idle`. The position must be inside the warehouse grid.")
def create_worker(payload: WorkerCreate, response: Response,
                  service: WorkforceService = Depends(get_workforce_service)) -> Worker:
    worker = service.create_worker(name=payload.name, worker_type=payload.type, speed=payload.speed,
                                   cur_x=payload.cur_x, cur_y=payload.cur_y, enabled=payload.enabled)
    response.headers["Location"] = f"/api/workers/{worker.id}"
    return worker


@router.patch("/{worker_id}", response_model=WorkerOut, responses={**NOT_FOUND, **INVALID},
              summary="Edit a worker",
              description="Send only the fields to change. `status` is controlled by the system.")
def update_worker(worker_id: int, payload: WorkerUpdate,
                  service: WorkforceService = Depends(get_workforce_service)) -> Worker:
    return service.update_worker(worker_id, payload.model_dump(exclude_unset=True))


@router.delete("/{worker_id}", status_code=204, response_class=Response,
               responses={**NOT_FOUND, 409: {"model": ErrorResponse, "description": "Worker is busy"}},
               summary="Delete a worker",
               description="Busy workers cannot be deleted; wait until they are idle.")
def delete_worker(worker_id: int, service: WorkforceService = Depends(get_workforce_service)) -> Response:
    service.delete_worker(worker_id)
    return Response(status_code=204)

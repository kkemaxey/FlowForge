"""HTTP endpoints for simulation: exceptions, picks, runs and the simulator's read endpoints.

Routers stay thin: each endpoint takes the validated request, calls one service function,
and turns the result into a response model. All the real logic is in service.py.
main.py mounts this router under /api/v1, so "/exceptions" is served at /api/v1/exceptions.
"""
from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

# get_db: opens a database session for the request and closes it afterwards.
from app.core.database import get_db
# get_current_user: checks the Firebase bearer token; responds 401 if it's missing or invalid.
from app.core.security import get_current_user
from app.modules.simulation import service
from app.modules.simulation.schemas import (
    ActiveAssignmentOut,
    ExceptionCreate,
    ExceptionOut,
    OpenExceptionOut,
    PickCreate,
    PickOut,
    RunCreate,
    RunOut,
    SkuStockOut,
    WorkerStatusOut,
)

# dependencies=[...] applies the login check to every endpoint in this router.
router = APIRouter(tags=["simulation"], dependencies=[Depends(get_current_user)])


# status_code=201: "Created". response_model: FastAPI sends back exactly ExceptionOut's fields.
@router.post("/tasks/{task_id}/exceptions", status_code=201, response_model=ExceptionOut)
def create_exception(
    # data: the JSON body, already validated by ExceptionCreate (bad input -> 422 before we get here).
    # task_id: from the URL; Path(gt=0) rejects 0 or negatives with a 422.
    # db: a database session provided by get_db.
    data: ExceptionCreate, task_id: int = Path(gt=0), db: Session = Depends(get_db)
) -> ExceptionOut:
    result = service.open_exception(db, task_id, data)
    exc = result.exception
    # Shape the response.
    return ExceptionOut(
        exception_id=exc.id,
        type=exc.type,
        task_id=exc.task_id,
        opened_at=exc.opened_at,
        task_status=result.task_status,
        rerouted_to_location_id=exc.rerouted_to_location_id,
    )


@router.get("/exceptions", response_model=list[OpenExceptionOut])
def list_exceptions(
    # ?open=true / ?open=false / omitted. Anything else (like ?open=maybe) -> 422.
    open: bool | None = Query(default=None, description="true: unresolved only; false: resolved only; omit: all"),
    # ?limit=N, between 1 and 500, default 100.
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[OpenExceptionOut]:
    # Build one response item per (exception, task) row from the service.
    return [
        OpenExceptionOut(
            exception_id=exc.id,
            type=exc.type,
            task_id=exc.task_id,
            order_id=task.order_id,
            assignment_id=exc.assignment_id,
            qty_found=exc.qty_found,
            from_location_id=exc.from_location_id,
            rerouted_to_location_id=exc.rerouted_to_location_id,
            task_status=task.status,
            opened_at=exc.opened_at,
            resolved_at=exc.resolved_at,
        )
        for exc, task in service.list_exceptions(db, open_only=open, limit=limit)
    ]


@router.post("/tasks/{task_id}/pick", response_model=PickOut)
def pick_task(data: PickCreate, task_id: int = Path(gt=0), db: Session = Depends(get_db)) -> PickOut:
    result = service.pick_task(db, task_id, data.assignment_id)
    return PickOut(
        task_id=result.task.id,
        task_status=result.task.status,
        assignment_id=result.assignment.id,
        worker_id=result.assignment.worker_id,
        order_id=result.order.id,
        order_status=result.order.status,
        picked_at=result.picked_at,
    )


def _run_out(run) -> RunOut:
    """Turn a SimRun row into the RunOut response shape (shared by the two run endpoints)."""
    return RunOut(run_id=run.id, seed=run.seed, started_at=run.started_at, ended_at=run.ended_at)


@router.get("/simulation/runs/active", response_model=RunOut)
def get_active_run(db: Session = Depends(get_db)) -> RunOut:
    # 404 if no run is active (raised inside the service).
    return _run_out(service.active_run(db))


@router.post("/simulation/runs", status_code=201, response_model=RunOut)
def start_run(data: RunCreate, db: Session = Depends(get_db)) -> RunOut:
    # Ends the current run (if any) and starts a new one.
    return _run_out(service.start_run(db, data.seed, data.config))


@router.get("/simulation/assignments/active", response_model=list[ActiveAssignmentOut])
def list_active_assignments(db: Session = Depends(get_db)) -> list[ActiveAssignmentOut]:
    # The simulator calls this every tick to see who is working on what.
    return [
        ActiveAssignmentOut(
            assignment_id=assignment.id,
            task_id=task.id,
            order_id=task.order_id,
            worker_id=worker.id,
            worker_x=worker.x,
            worker_y=worker.y,
            worker_speed=worker.speed,
            location_id=location.id,
            location_x=location.x,
            location_y=location.y,
            sku_code=sku_code,
            qty=task.qty,
            bin_on_hand=on_hand,
            started_at=assignment.started_at,
        )
        # Each service row unpacks into these six values.
        for assignment, task, worker, location, sku_code, on_hand in service.active_assignments(db)
    ]


@router.get("/inventory/skus", response_model=list[SkuStockOut])
def list_available_skus(db: Session = Depends(get_db)) -> list[SkuStockOut]:
    # The order generator calls this so it only orders products that are in stock.
    return [SkuStockOut(sku_code=code, available=available) for code, available in service.available_skus(db)]


@router.post("/simulation/workers/{worker_id}/recover", response_model=WorkerStatusOut)
def recover_worker(worker_id: int = Path(gt=0), db: Session = Depends(get_db)) -> WorkerStatusOut:
    # The simulator calls this when a downed worker's downtime is over.
    worker = service.recover_worker(db, worker_id)
    return WorkerStatusOut(worker_id=worker.id, status=worker.status)

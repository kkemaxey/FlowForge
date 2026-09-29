from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.error_handlers import ErrorResponse
from app.modules.metrics.repository import SqlEventRepository
from app.modules.metrics.schema import EventCreate, EventOut, MetricsOut
from app.modules.metrics.service import EventRecord, MetricsService, MetricsSnapshot
from app.modules.workforce.repository import SqlWorkerRepository


def get_metrics_service(session: Session = Depends(get_session)) -> MetricsService:
    return MetricsService(SqlEventRepository(session), SqlWorkerRepository(session))


router = APIRouter(prefix="/api", tags=["events & metrics"])

INVALID = {422: {"model": ErrorResponse, "description": "Validation or business-rule failure"}}


@router.post("/events", response_model=EventOut, status_code=201, responses=INVALID,
             summary="Record a warehouse event",
             description="Called by the worker simulator. Task events need `task_id`; "
                         "`task_picked` also needs `qty` of at least 1. The server sets `ts`.")
def create_event(payload: EventCreate,
                 service: MetricsService = Depends(get_metrics_service)) -> EventRecord:
    return service.record_event(event_type=payload.type, task_id=payload.task_id,
                                worker_id=payload.worker_id, qty=payload.qty, payload=payload.payload)


@router.get("/metrics", response_model=MetricsOut, responses=INVALID,
            summary="Throughput, WIP, and worker metrics",
            description="Aggregates events from the last `window_minutes` (1-1440, default 60). "
                        "WIP counts tasks currently assigned but not yet picked or failed.")
def get_metrics(window_minutes: int = 60,
                service: MetricsService = Depends(get_metrics_service)) -> MetricsSnapshot:
    return service.snapshot(window_minutes)

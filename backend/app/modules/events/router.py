from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.events import service
from app.modules.events.schemas import LiveMetrics, ThroughputBucket

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.get("/metrics", response_model=LiveMetrics)
def live_metrics(db: Session = Depends(get_db)) -> LiveMetrics:
    """Throughput over the last 5 minutes as hourly rates, and the newest open exception."""
    return service.live_metrics(db)


@router.get("/metrics/throughput", response_model=list[ThroughputBucket])
def throughput(minutes: int = Query(default=30, ge=1, le=1440), db: Session = Depends(get_db)) -> list[ThroughputBucket]:
    """Units and tasks picked per minute over the last `minutes`, oldest first."""
    return service.throughput(db, minutes)

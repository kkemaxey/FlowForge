"""HTTP endpoints for metrics. Mounted under /api/v1 by main.py."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.events import service
from app.modules.events.schemas import ThroughputOut

# Every endpoint here requires a valid Firebase login.
router = APIRouter(tags=["events"], dependencies=[Depends(get_current_user)])


@router.get("/metrics/throughput", response_model=ThroughputOut)
def get_throughput(
    # ?run_id=12 — required, must be a positive integer (otherwise 422).
    run_id: int = Query(gt=0),
    # ?window_minutes=5 — optional, 1 to 1440 (one day), default 5.
    window_minutes: int = Query(default=5, ge=1, le=1440),
    db: Session = Depends(get_db),
) -> ThroughputOut:
    # Unknown run -> 404 (raised inside the service).
    picks, as_of = service.throughput(db, run_id, window_minutes)
    return ThroughputOut(
        run_id=run_id,
        window_minutes=window_minutes,
        picks=picks,
        # Average picks per minute over the window, rounded to 2 decimals.
        picks_per_min=round(picks / window_minutes, 2),
        as_of=as_of,
    )

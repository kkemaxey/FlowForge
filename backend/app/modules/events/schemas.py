"""Response bodies for /api/v1/events. The live board reads these shapes."""
from pydantic import BaseModel

from app.core.schemas import UtcDatetime
from app.modules.simulation.models import ExceptionType


class ActiveException(BaseModel):
    task_id: int
    order_id: int
    location: str  # e.g. "A2 (4,2)"
    type: ExceptionType
    raised_at: UtcDatetime


class LiveMetrics(BaseModel):
    units_per_hour: int
    tasks_per_hour: int
    active_exception: ActiveException | None
    as_of: UtcDatetime


class ThroughputBucket(BaseModel):
    """What was picked in the minute starting at bucket_start."""

    bucket_start: UtcDatetime
    units: int
    tasks: int

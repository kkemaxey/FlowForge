from pydantic import BaseModel

# Reuse the simulation module's timestamp format (UTC, milliseconds, trailing "Z").
from app.modules.simulation.schemas import UtcDateTime


class ThroughputOut(BaseModel):
    """Response of GET /metrics/throughput."""

    run_id: int
    window_minutes: int
    # task_picked events in the window.
    picks: int
    # picks / window_minutes.
    picks_per_min: float
    # The end of the window (when the count was taken).
    as_of: UtcDateTime

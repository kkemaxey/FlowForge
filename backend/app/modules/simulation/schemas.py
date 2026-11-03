"""Request/response shapes for exceptions and simulation endpoints.

These are Pydantic models. FastAPI uses them two ways:
- Request models (…Create) check incoming JSON. If a field is missing, the wrong type, or breaks
  a rule like gt=0, FastAPI rejects the request with a 422 before our code runs.
- Response models (…Out) define exactly which fields go back to the caller, and in what format.
"""
from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator


def _iso_utc_ms(value: datetime) -> str:
    """Format a datetime as UTC ISO 8601 with milliseconds, e.g. "2026-11-02T14:03:07.123Z"."""
    # If the datetime carries a timezone, convert it to UTC and drop the timezone info.
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    # Date and time to the second, then 3-digit milliseconds, then "Z" (which means UTC).
    return value.strftime("%Y-%m-%dT%H:%M:%S.") + f"{value.microsecond // 1000:03d}Z"


# A datetime type that always turns into the string format above when sent as JSON.
# The database stores naive (timezone-less) UTC times, so this is how they reach the frontend.
UtcDateTime = Annotated[datetime, PlainSerializer(_iso_utc_ms, return_type=str)]

# The only three exception types accepted. Anything else is rejected with a 422.
ExceptionType = Literal["stockout", "jam", "worker_down"]


class ExceptionCreate(BaseModel):
    """Body of POST /tasks/{task_id}/exceptions."""

    # Reject any field we don't recognise (catches typos like "qty_fnd").
    model_config = ConfigDict(extra="forbid")

    type: ExceptionType
    # The active assignment being interrupted. gt=0: must be a positive number.
    assignment_id: int = Field(gt=0)
    # Units actually in the bin. Required for stockout, where it corrects the bin's on_hand.
    # ge=0: can't be negative. default=None: optional unless the rule below says otherwise.
    qty_found: int | None = Field(default=None, ge=0)

    # Runs after the individual fields pass their checks, to enforce a rule across fields.
    @model_validator(mode="after")
    def stockout_needs_qty_found(self) -> "ExceptionCreate":
        if self.type == "stockout" and self.qty_found is None:
            # Raising ValueError here becomes a 422 response.
            raise ValueError("qty_found is required for a stockout")
        return self


class ExceptionOut(BaseModel):
    """201 response of POST /tasks/{task_id}/exceptions."""

    exception_id: int
    type: ExceptionType
    task_id: int
    opened_at: UtcDateTime
    # Where the task ended up: "open" (rerouted or reopened) or "exception" (waiting for supervisor).
    task_status: str
    # The new bin, or null if the task couldn't be rerouted.
    rerouted_to_location_id: int | None


class OpenExceptionOut(BaseModel):
    """One row of GET /exceptions: the exception plus some task context for the console."""

    exception_id: int
    type: ExceptionType
    task_id: int
    order_id: int
    assignment_id: int
    qty_found: int | None
    from_location_id: int
    rerouted_to_location_id: int | None
    # The task's status right now (it may have moved on since the exception).
    task_status: str
    opened_at: UtcDateTime
    resolved_at: UtcDateTime | None


class PickCreate(BaseModel):
    """Body of POST /tasks/{task_id}/pick."""

    model_config = ConfigDict(extra="forbid")

    # The active assignment that just finished the pick.
    assignment_id: int = Field(gt=0)


class PickOut(BaseModel):
    """Response of POST /tasks/{task_id}/pick."""

    task_id: int
    # "picked", or "complete" if this pick finished the whole order.
    task_status: str
    assignment_id: int
    worker_id: int
    order_id: int
    # "complete" once every task in the order is picked.
    order_status: str
    picked_at: UtcDateTime


class RunCreate(BaseModel):
    """Body of POST /simulation/runs. Both fields are optional and just recorded on the run."""

    model_config = ConfigDict(extra="forbid")

    seed: int | None = None
    config: dict | None = None


class RunOut(BaseModel):
    """A simulation run, as returned by the runs endpoints."""

    run_id: int
    seed: int | None
    started_at: UtcDateTime
    # null while the run is still active.
    ended_at: UtcDateTime | None


class ActiveAssignmentOut(BaseModel):
    """Everything the simulator needs to time and finish one pick."""

    assignment_id: int
    task_id: int
    order_id: int
    worker_id: int
    # Where the worker is standing now, and how fast they move (grid cells per second).
    worker_x: int
    worker_y: int
    worker_speed: float
    # The bin they're walking to.
    location_id: int
    location_x: int
    location_y: int
    sku_code: str
    # How many units to pick.
    qty: int
    # How many units the bin really holds. If less than qty, the simulator raises a stockout.
    bin_on_hand: int
    started_at: UtcDateTime


class SkuStockOut(BaseModel):
    """One row of GET /inventory/skus: a SKU and its total unreserved stock across all bins."""

    sku_code: str
    available: int


class WorkerStatusOut(BaseModel):
    """Response of POST /simulation/workers/{id}/recover."""

    worker_id: int
    status: str

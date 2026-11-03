"""Request and response bodies for the simulation endpoints."""
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.schemas import UtcDatetime
from app.modules.orders.models import OrderStatus
from app.modules.simulation.models import ExceptionType
from app.modules.tasks.models import TaskStatus
from app.modules.workforce.models import WorkerStatus


class PickCreate(BaseModel):
    """Body of POST /api/v1/tasks/{task_id}/pick."""

    model_config = ConfigDict(extra="forbid")

    # The active assignment that just finished the pick.
    assignment_id: int = Field(gt=0)


class PickOut(BaseModel):
    task_id: int
    status: TaskStatus
    version: int
    assignment_id: int
    worker_id: int
    order_id: int
    order_status: OrderStatus
    picked_at: UtcDatetime


class ExceptionCreate(BaseModel):
    """Body of POST /api/v1/tasks/{task_id}/exceptions."""

    model_config = ConfigDict(extra="forbid")

    type: ExceptionType
    # The active assignment being interrupted.
    assignment_id: int = Field(gt=0)
    # Units actually in the bin. Required for a stockout, where it corrects the bin's stock.
    qty_found: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def stockout_needs_qty_found(self) -> "ExceptionCreate":
        if self.type is ExceptionType.stockout and self.qty_found is None:
            raise ValueError("qty_found is required for a stockout")
        return self


class ExceptionOut(BaseModel):
    exception_id: int
    type: ExceptionType
    task_id: int
    opened_at: UtcDatetime
    # open: rerouted or reopened, back in the queue. exception: waiting for the supervisor.
    task_status: TaskStatus
    rerouted_to_location_id: int | None


class ExceptionListItem(BaseModel):
    exception_id: int
    type: ExceptionType
    task_id: int
    order_id: int
    assignment_id: int | None
    qty_found: int | None
    from_location_id: int
    rerouted_to_location_id: int | None
    # The task's status now, which may have moved on since the exception.
    task_status: TaskStatus
    opened_at: UtcDatetime
    resolved_at: UtcDatetime | None


class ExceptionListOut(BaseModel):
    items: list[ExceptionListItem]
    count: int  # number of items in this response


class WorkerRecoveredOut(BaseModel):
    worker_id: int
    status: WorkerStatus


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
    qty: int
    # How many units the bin really holds. If less than qty, the simulator raises a stockout.
    bin_on_hand: int
    assigned_at: UtcDatetime


class ActiveAssignmentListOut(BaseModel):
    items: list[ActiveAssignmentOut]
    count: int  # number of items in this response

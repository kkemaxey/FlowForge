"""Request and response bodies for the simulation endpoints."""
from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import UtcDatetime
from app.modules.orders.models import OrderStatus
from app.modules.tasks.models import TaskStatus


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

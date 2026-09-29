"""Request and response shapes for orders, tasks and the live board."""
import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, PlainSerializer, field_validator

from app.core.clock import format_utc
from app.modules.orders.order_status import OrderPriority, OrderStatus
from app.modules.orders.task_states import TaskStatus

# Storage location ids from the course map seed, e.g. "A1-01" or "C4-11".
LOCATION_ID_PATTERN = re.compile(r"^[A-Z]\d{1,2}-\d{2}$")

# Stored times are naive UTC; send them to clients with a trailing Z.
UtcDateTime = Annotated[datetime, PlainSerializer(format_utc, return_type=str)]


class OrderLineCreate(BaseModel):
    sku_id: str = Field(min_length=1, max_length=40, examples=["SKU-88213"])
    qty: int = Field(gt=0, le=500, examples=[4])
    location_id: str = Field(examples=["A1-01"],
                             description="Where the SKU is stored (a map-seed location id).")

    @field_validator("sku_id")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("location_id")
    @classmethod
    def location_id_format(cls, value: str) -> str:
        value = value.strip().upper()
        if not LOCATION_ID_PATTERN.match(value):
            raise ValueError("location_id must look like 'A1-01' (aisle-slot)")
        return value


class OrderCreate(BaseModel):
    due_at: datetime = Field(description="When the order must be picked by (ISO 8601).")
    priority: OrderPriority = OrderPriority.NORMAL
    lines: list[OrderLineCreate] = Field(min_length=1, max_length=50)


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    worker_id: int | None = Field(default=None, gt=0,
                                  description="Required when status is 'assigned'.")


class TaskView(BaseModel):
    id: int
    order_id: int
    order_line_id: int
    sku_id: str
    location_id: str
    qty: int
    status: TaskStatus
    worker_id: int | None
    assigned_at: UtcDateTime | None
    completed_at: UtcDateTime | None


class OrderView(BaseModel):
    id: int
    status: OrderStatus
    priority: OrderPriority
    created_at: UtcDateTime
    due_at: UtcDateTime
    tasks: list[TaskView]


class BoardCard(BaseModel):
    task_id: int
    order_id: int
    sku_id: str
    location_id: str
    qty: int
    priority: OrderPriority
    worker_id: int | None
    due_at: UtcDateTime
    minutes_until_due: int
    is_late: bool


class BoardSummary(BaseModel):
    total_tasks: int
    work_in_progress: int
    exceptions: int
    late_orders: int
    picked_last_hour: int


class LiveBoard(BaseModel):
    generated_at: UtcDateTime
    summary: BoardSummary
    orders_by_status: dict[OrderStatus, int]
    columns: dict[TaskStatus, list[BoardCard]]

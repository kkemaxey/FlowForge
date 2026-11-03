"""Request and response bodies for /api/v1/orders."""
from pydantic import BaseModel, Field

from app.core.schemas import UtcDatetime
from app.modules.orders.models import OrderStatus
from app.modules.tasks.models import TaskStatus
from app.modules.warehouse.schemas import LocationOut


class OrderLineIn(BaseModel):
    sku_code: str = Field(min_length=1, max_length=32)
    qty: int = Field(ge=1)


class OrderCreate(BaseModel):
    external_ref: str = Field(min_length=1, max_length=64)
    run_id: int | None = None
    # Capped below TINYINT's 127 to leave headroom for expedite to raise it.
    priority: int = Field(default=0, ge=0, le=100)
    due_at: UtcDatetime | None = None
    lines: list[OrderLineIn] = Field(min_length=1)


class OrderTaskOut(BaseModel):
    task_id: int
    qty: int
    status: TaskStatus
    version: int
    location: LocationOut


class OrderLineOut(BaseModel):
    order_line_id: int
    sku_code: str
    qty_ordered: int
    tasks: list[OrderTaskOut]


class OrderOut(BaseModel):
    order_id: int
    external_ref: str
    run_id: int | None
    status: OrderStatus
    priority: int
    expedited: bool
    due_at: UtcDatetime | None
    created_at: UtcDatetime
    lines: list[OrderLineOut]

"""Request and response shapes for the tasks and live-board API."""
import re
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, field_validator

from app.core.clock import format_utc
from app.modules.tasks.task_states import TaskPriority, TaskStatus

BIN_LOCATION_PATTERN = re.compile(r"^[A-Z]-\d{2}-\d{1,2}$")

# Stored times are naive UTC; send them to clients with a trailing Z.
UtcDateTime = Annotated[datetime, PlainSerializer(format_utc, return_type=str)]


class TaskCreate(BaseModel):
    order_ref: str = Field(min_length=1, max_length=40, examples=["ORD-10442"])
    sku: str = Field(min_length=1, max_length=40, examples=["SKU-88213"])
    bin_location: str = Field(examples=["B-07-3"],
                              description="Aisle letter, bay number, shelf level.")
    quantity: int = Field(gt=0, le=500, examples=[4])
    priority: TaskPriority = TaskPriority.NORMAL
    due_at: datetime = Field(description="When the order must be picked by (ISO 8601).")

    @field_validator("bin_location")
    @classmethod
    def bin_location_format(cls, value: str) -> str:
        value = value.strip().upper()
        if not BIN_LOCATION_PATTERN.match(value):
            raise ValueError("bin_location must look like 'B-07-3' (aisle-bay-level)")
        return value


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    worker_id: int | None = Field(default=None, gt=0,
                                  description="Required when status is 'assigned'.")
    reason: str | None = Field(default=None, max_length=200,
                               description="Required when status is 'exception'.")


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_ref: str
    sku: str
    bin_location: str
    quantity: int
    priority: TaskPriority
    status: TaskStatus
    assigned_worker_id: int | None
    due_at: UtcDateTime
    created_at: UtcDateTime
    updated_at: UtcDateTime
    completed_at: UtcDateTime | None
    exception_reason: str | None


class BoardCard(BaseModel):
    id: int
    order_ref: str
    sku: str
    bin_location: str
    quantity: int
    priority: TaskPriority
    assigned_worker_id: int | None
    due_at: UtcDateTime
    minutes_until_due: int
    is_late: bool


class BoardSummary(BaseModel):
    total_tasks: int
    work_in_progress: int
    late_tasks: int
    exceptions: int
    picked_last_hour: int


class LiveBoard(BaseModel):
    generated_at: UtcDateTime
    summary: BoardSummary
    columns: dict[TaskStatus, list[BoardCard]]

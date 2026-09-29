"""Pydantic models that define the HTTP contract."""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing_extensions import Literal

WorkerType = Literal["human", "robot"]
WorkerStatus = Literal["idle", "busy"]


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class WorkerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=64, examples=["Picker Ana"])
    type: WorkerType
    speed: float = Field(ge=0.1, le=10.0, description="Grid cells per time step")
    cur_x: int = Field(ge=0, description="Column on the warehouse grid")
    cur_y: int = Field(ge=0, description="Row on the warehouse grid")
    enabled: bool = True


class WorkerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=64)
    type: Optional[WorkerType] = None
    speed: Optional[float] = Field(default=None, ge=0.1, le=10.0)
    cur_x: Optional[int] = Field(default=None, ge=0)
    cur_y: Optional[int] = Field(default=None, ge=0)
    enabled: Optional[bool] = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self):
        null_fields = sorted(name for name in self.model_fields_set if getattr(self, name) is None)
        if null_fields:
            raise ValueError(f"fields cannot be null: {', '.join(null_fields)}")
        return self


class WorkerOut(BaseModel):
    id: int
    name: str
    type: WorkerType
    speed: float
    cur_x: int
    cur_y: int
    status: WorkerStatus
    enabled: bool


EventType = Literal["task_assigned", "task_picked", "task_exception", "order_completed"]


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: EventType
    task_id: Optional[int] = Field(default=None, ge=1)
    worker_id: Optional[int] = Field(default=None, ge=1)
    qty: Optional[int] = Field(default=None, description="Units picked; required for task_picked")
    payload: Optional[Dict[str, Any]] = Field(default=None, examples=[{"reason": "stockout"}])


class EventOut(BaseModel):
    id: int
    ts: datetime
    type: EventType
    task_id: Optional[int]
    worker_id: Optional[int]
    qty: Optional[int]
    payload: Optional[Dict[str, Any]]


class WorkerCountsOut(BaseModel):
    idle: int
    busy: int
    disabled: int


class MetricsOut(BaseModel):
    window_minutes: int
    units_picked: int
    throughput_per_hour: float
    wip: int
    exceptions: int
    workers: WorkerCountsOut

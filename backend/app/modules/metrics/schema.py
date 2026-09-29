"""Pydantic models that define the events and metrics HTTP contract."""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Literal

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

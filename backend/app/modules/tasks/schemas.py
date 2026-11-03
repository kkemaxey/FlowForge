"""Response bodies for /api/v1/tasks."""
from pydantic import BaseModel

from app.core.schemas import UtcDatetime
from app.modules.assignment.models import AssignmentSource
from app.modules.tasks.models import TaskStatus
from app.modules.warehouse.schemas import LocationOut


class CurrentAssignmentOut(BaseModel):
    assignment_id: int
    worker_id: int
    source: AssignmentSource
    assigned_at: UtcDatetime


class TaskOut(BaseModel):
    task_id: int
    order_id: int
    order_line_id: int
    sku_code: str
    qty: int
    location: LocationOut
    status: TaskStatus
    priority: int
    version: int
    created_at: UtcDatetime
    current_assignment: CurrentAssignmentOut | None


class TaskListOut(BaseModel):
    items: list[TaskOut]
    count: int  # number of items in this response

"""Request and response bodies for /api/v1/assignments."""
from pydantic import BaseModel, Field

from app.core.schemas import UtcDatetime
from app.modules.assignment.models import AssignmentOutcome, AssignmentSource
from app.modules.tasks.models import TaskStatus


class RunRequest(BaseModel):
    algorithm: str = "greedy_v1"
    # Tags the events this pass writes; defaults to each task's order run_id.
    run_id: int | None = None


class AssignmentOut(BaseModel):
    assignment_id: int
    task_id: int
    worker_id: int
    source: AssignmentSource
    score: float
    assigned_at: UtcDatetime


class RunResult(BaseModel):
    algorithm: str
    assignments: list[AssignmentOut]
    # Pairings dropped because the task or worker changed mid-pass; retried next pass.
    conflicts: int


class ReassignRequest(BaseModel):
    worker_id: int
    # The task version the supervisor was looking at; 409 if the task changed since.
    expected_version: int = Field(ge=0)
    reason: str | None = Field(default=None, max_length=255)


class NewAssignmentOut(BaseModel):
    assignment_id: int
    worker_id: int
    source: AssignmentSource
    assigned_at: UtcDatetime


class PreviousAssignmentOut(BaseModel):
    assignment_id: int
    worker_id: int
    outcome: AssignmentOutcome
    ended_at: UtcDatetime


class ReassignResult(BaseModel):
    task_id: int
    status: TaskStatus
    version: int
    assignment: NewAssignmentOut
    # null when the task had no current assignment (open, or stuck in exception)
    previous_assignment: PreviousAssignmentOut | None

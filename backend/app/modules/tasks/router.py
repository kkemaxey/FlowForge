from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.assignment import service as assignment_service
from app.modules.assignment.schemas import ReassignRequest, ReassignResult
from app.modules.tasks import service
from app.modules.tasks.models import TaskStatus
from app.modules.tasks.schemas import TaskListOut

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])


@router.get("", response_model=TaskListOut)
def list_tasks(
    status: TaskStatus | None = Query(default=None, description="open = the work queue"),
    limit: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> TaskListOut:
    return service.list_tasks(db, status, limit)


@router.post("/{task_id}/reassign", response_model=ReassignResult)
def reassign_task(task_id: int, payload: ReassignRequest, db: Session = Depends(get_db)) -> ReassignResult:
    """Supervisor moves a task to an idle worker (or assigns an open/exception task directly).

    A POST, not a PATCH, because it creates a new assignment record.
    """
    return assignment_service.reassign(db, task_id, payload)

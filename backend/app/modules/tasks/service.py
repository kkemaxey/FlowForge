"""Task state machine and the task list (the work queue).

Every task status change goes through transition(). It is a compare-and-set: the UPDATE only
matches if the task still has the status and version the caller read, so when the assigner,
the simulator, and a supervisor race on the same task, exactly one wins and the rest get a
TaskConflict (409) instead of silently overwriting each other.

    open ──────► assigned ──────► picked (final)
     ▲  ◄──────── │  ▲ │
     │            │  └─┘ assigned → assigned: reassigned to another worker
     │            ▼
     └──────── exception ───► assigned (supervisor assigns it directly)
"""
from sqlalchemy import and_, select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.core.database import utcnow
from app.core.errors import ApiError
from app.modules.assignment.models import Assignment
from app.modules.tasks.models import Task, TaskStatus
from app.modules.tasks.schemas import CurrentAssignmentOut, TaskListOut, TaskOut
from app.modules.warehouse.models import Location, Sku
from app.modules.warehouse.schemas import LocationOut

ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    # Assigner or supervisor hands it to a worker.
    TaskStatus.open: {TaskStatus.assigned},
    # Picked; reassigned to another worker; sent back to the queue (rerouted stockout, worker
    # down); or stuck because no bin anywhere has the stock.
    TaskStatus.assigned: {TaskStatus.picked, TaskStatus.assigned, TaskStatus.open, TaskStatus.exception},
    # Supervisor resolves it: back to the queue, or straight to a worker.
    TaskStatus.exception: {TaskStatus.open, TaskStatus.assigned},
    TaskStatus.picked: set(),
}


class TaskConflict(ApiError):
    """The task is not in the state the caller expected. Always a 409."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(409, code, detail)


def transition(
    session: Session,
    task: Task,
    from_status: TaskStatus,
    to_status: TaskStatus,
    expected_version: int | None = None,
) -> None:
    """Move task from from_status to to_status and bump its version, or raise TaskConflict.

    expected_version defaults to the version on the loaded task; pass the client's value when an
    API request carries one (e.g. reassign's expected_version).

    Does not commit: the caller commits once, together with its other writes (assignment rows,
    worker status, its events row), so they all succeed or fail as one transaction. On a
    TaskConflict the caller should roll back.
    """
    if to_status not in ALLOWED_TRANSITIONS[from_status]:
        raise TaskConflict(
            "invalid_transition", f"Task {task.id} cannot move from {from_status.value} to {to_status.value}"
        )

    version = task.version if expected_version is None else expected_version
    result = session.execute(
        update(Task)
        .where(Task.id == task.id, Task.status == from_status, Task.version == version)
        .values(status=to_status, version=Task.version + 1, updated_at=utcnow())
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise TaskConflict(
            "version_conflict",
            f"Task {task.id} is no longer {from_status.value} at version {version}; reload and retry",
        )

    # Mirror the new row on the loaded object without marking it dirty (no second UPDATE).
    set_committed_value(task, "status", to_status)
    set_committed_value(task, "version", version + 1)


def list_tasks(session: Session, status: TaskStatus | None, limit: int) -> TaskListOut:
    """Tasks sorted priority DESC, created_at ASC. With status=open this is the work queue."""
    query = (
        select(Task, Sku.code, Location, Assignment)
        .join(Sku, Sku.id == Task.sku_id)
        .join(Location, Location.id == Task.location_id)
        # At most one open assignment per task (uq_one_open_per_task), so no duplicate rows.
        .outerjoin(Assignment, and_(Assignment.task_id == Task.id, Assignment.ended_at.is_(None)))
        .order_by(Task.priority.desc(), Task.created_at, Task.id)
        .limit(limit)
    )
    if status is not None:
        query = query.where(Task.status == status)

    items = [
        TaskOut(
            task_id=task.id,
            order_id=task.order_id,
            order_line_id=task.order_line_id,
            sku_code=sku_code,
            qty=task.qty,
            location=LocationOut.of(location),
            status=task.status,
            priority=task.priority,
            version=task.version,
            created_at=task.created_at,
            current_assignment=(
                CurrentAssignmentOut(
                    assignment_id=assignment.id,
                    worker_id=assignment.worker_id,
                    source=assignment.source,
                    assigned_at=assignment.assigned_at,
                )
                if assignment is not None
                else None
            ),
        )
        for task, sku_code, location, assignment in session.execute(query)
    ]
    return TaskListOut(items=items, count=len(items))

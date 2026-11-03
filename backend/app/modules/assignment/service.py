"""The scheduler: pair open tasks with idle workers. Also the supervisor's reassign override.

A pass has two steps:
  1. Plan, in memory: the algorithm pairs a snapshot of idle workers with a snapshot of open tasks.
  2. Write each pairing in its own transaction: task open -> assigned (compare-and-set via
     transition()), worker idle -> busy (compare-and-set), a new assignments row, and a
     task_assigned event. If anything changed since the snapshot (the simulator, a supervisor, or
     another pass got there first), that pairing rolls back and counts as a conflict; the task is
     still open and the next pass retries it.
"""
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.errors import ApiError
from app.modules.assignment.models import Assignment, AssignmentOutcome, AssignmentSource
from app.modules.assignment.schemas import (
    AssignmentOut,
    NewAssignmentOut,
    PreviousAssignmentOut,
    ReassignRequest,
    ReassignResult,
    RunResult,
)
from app.modules.events.models import Event
from app.modules.orders.models import Order
from app.modules.simulation.models import SimRun, TaskException
from app.modules.tasks.models import Task, TaskStatus
from app.modules.tasks.service import TaskConflict, transition
from app.modules.warehouse.models import Location
from app.modules.workforce.models import Worker, WorkerStatus


@dataclass(frozen=True)
class WorkerSnapshot:
    id: int
    x: int
    y: int


@dataclass(frozen=True)
class TaskSnapshot:
    id: int
    version: int
    x: int
    y: int
    order_id: int
    run_id: int | None


@dataclass(frozen=True)
class Pairing:
    worker: WorkerSnapshot
    task: TaskSnapshot
    score: float


def manhattan(worker: WorkerSnapshot, task: TaskSnapshot) -> float:
    return float(abs(worker.x - task.x) + abs(worker.y - task.y))


def greedy(
    workers: list[WorkerSnapshot], tasks: list[TaskSnapshot], score: Callable[[WorkerSnapshot, TaskSnapshot], float]
) -> list[Pairing]:
    """Each worker in turn takes the remaining task with the lowest score.

    Ties go to the task that comes first in `tasks` (oldest). Priority is deliberately not used:
    in greedy_v1, expedite only reorders the queue, not who gets assigned.
    """
    remaining = list(tasks)
    pairings = []
    for worker in workers:
        if not remaining:
            break
        best = min(remaining, key=lambda task: score(worker, task))
        pairings.append(Pairing(worker, best, score(worker, best)))
        remaining.remove(best)
    return pairings


# Algorithm name -> planner. To try a different score (e.g. distance minus priority and age
# weights), add an entry here; the write step and the API stay the same.
ALGORITHMS: dict[str, Callable[[list[WorkerSnapshot], list[TaskSnapshot]], list[Pairing]]] = {
    "greedy_v1": lambda workers, tasks: greedy(workers, tasks, manhattan),
}


def run_pass(session: Session, algorithm: str = "greedy_v1", run_id: int | None = None) -> RunResult:
    """Run one assigner pass. Commits each pairing separately."""
    planner = ALGORITHMS.get(algorithm)
    if planner is None:
        raise ApiError(422, "unknown_algorithm", f"Unknown algorithm {algorithm!r}; known: {', '.join(ALGORITHMS)}")
    if run_id is not None and session.get(SimRun, run_id) is None:
        raise ApiError(422, "unknown_run", f"run_id {run_id} does not exist")

    workers = _idle_workers(session)
    tasks = _open_tasks(session) if workers else []
    session.rollback()  # end the read transaction; each pairing gets a fresh one

    made, conflicts = [], 0
    for pairing in planner(workers, tasks):
        assignment = _write_pairing(session, pairing, algorithm, run_id)
        if assignment is None:
            conflicts += 1
        else:
            made.append(assignment)
    return RunResult(algorithm=algorithm, assignments=made, conflicts=conflicts)


def _idle_workers(session: Session) -> list[WorkerSnapshot]:
    rows = session.execute(
        select(Worker.id, Worker.x, Worker.y)
        .where(Worker.status == WorkerStatus.idle, Worker.is_active.is_(True))
        .order_by(Worker.id)
    )
    return [WorkerSnapshot(*row) for row in rows]


def _open_tasks(session: Session) -> list[TaskSnapshot]:
    rows = session.execute(
        select(Task.id, Task.version, Location.x, Location.y, Task.order_id, Order.run_id)
        .join(Location, Location.id == Task.location_id)
        .join(Order, Order.id == Task.order_id)
        .where(Task.status == TaskStatus.open)
        .order_by(Task.created_at, Task.id)
    )
    return [TaskSnapshot(*row) for row in rows]


def _write_pairing(session: Session, pairing: Pairing, algorithm: str, run_id: int | None) -> AssignmentOut | None:
    """Commit one pairing atomically. Returns None (rolled back) if the task or worker moved on."""
    worker, snapshot = pairing.worker, pairing.task
    try:
        task = session.get(Task, snapshot.id)
        if task is None:
            raise TaskConflict("task_not_found", f"Task {snapshot.id} no longer exists")
        transition(session, task, TaskStatus.open, TaskStatus.assigned, expected_version=snapshot.version)

        busy = session.execute(
            update(Worker)
            .where(Worker.id == worker.id, Worker.status == WorkerStatus.idle, Worker.is_active.is_(True))
            .values(status=WorkerStatus.busy)
            .execution_options(synchronize_session=False)
        )
        if busy.rowcount != 1:
            raise TaskConflict("worker_unavailable", f"Worker {worker.id} is no longer idle")

        assignment = Assignment(
            task_id=task.id,
            worker_id=worker.id,
            source=AssignmentSource.scheduler,
            algorithm=algorithm,
            score=pairing.score,
        )
        session.add(assignment)
        session.flush()  # the one-open-assignment unique keys reject a race here
        session.add(
            Event(
                event_type="task_assigned",
                run_id=run_id if run_id is not None else snapshot.run_id,
                order_id=snapshot.order_id,
                task_id=task.id,
                worker_id=worker.id,
                assignment_id=assignment.id,
                payload={"source": "scheduler", "algorithm": algorithm, "score": pairing.score},
            )
        )
        session.commit()
    except (TaskConflict, IntegrityError):
        session.rollback()
        return None
    except Exception:
        session.rollback()
        raise

    return AssignmentOut(
        assignment_id=assignment.id,
        task_id=task.id,
        worker_id=worker.id,
        source=assignment.source,
        score=pairing.score,
        assigned_at=assignment.assigned_at,
    )


def reassign(session: Session, task_id: int, request: ReassignRequest) -> ReassignResult:
    """Supervisor override: give a task to a specific idle worker, in one transaction.

    If the task has an open assignment, it is closed with outcome 'reassigned' and its worker is
    freed. If it has none (open, or stuck in exception), the task is assigned directly, and a stuck
    task's open exception is marked resolved. Raises
    404 if the task or worker doesn't exist, 409 if the expected_version is stale, the task is
    picked, the target worker isn't idle and active, or a concurrent write wins the unique keys.
    """
    try:
        result = _reassign(session, task_id, request)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise TaskConflict("assignment_conflict", f"Task {task_id} or worker {request.worker_id} was just assigned elsewhere")
    except Exception:
        session.rollback()
        raise
    return result


def _reassign(session: Session, task_id: int, request: ReassignRequest) -> ReassignResult:
    task = session.get(Task, task_id)
    if task is None:
        raise ApiError(404, "task_not_found", f"Task {task_id} not found")
    if session.get(Worker, request.worker_id) is None:
        raise ApiError(404, "worker_not_found", f"Worker {request.worker_id} not found")

    # Compare-and-set on the version the supervisor saw. picked -> assigned is not an allowed
    # move, so a finished task is rejected here with invalid_transition.
    was_stuck = task.status is TaskStatus.exception
    transition(session, task, task.status, TaskStatus.assigned, expected_version=request.expected_version)

    # Claim the target before freeing anyone, so "reassign to the worker who already has it" is
    # rejected (that worker is busy) instead of closing and reopening the same pairing.
    claimed = session.execute(
        update(Worker)
        .where(Worker.id == request.worker_id, Worker.status == WorkerStatus.idle, Worker.is_active.is_(True))
        .values(status=WorkerStatus.busy)
        .execution_options(synchronize_session=False)
    )
    if claimed.rowcount != 1:
        raise TaskConflict("worker_unavailable", f"Worker {request.worker_id} is not idle and active")

    now = utcnow()
    previous = session.scalar(
        select(Assignment).where(Assignment.task_id == task.id, Assignment.ended_at.is_(None)).with_for_update()
    )
    if previous is not None:
        previous.ended_at = now
        previous.outcome = AssignmentOutcome.reassigned
        # Free the old worker only if it is still busy with this task (a worker marked down stays down).
        session.execute(
            update(Worker)
            .where(Worker.id == previous.worker_id, Worker.status == WorkerStatus.busy)
            .values(status=WorkerStatus.idle)
            .execution_options(synchronize_session=False)
        )
        session.flush()  # close it before opening the new one (one open assignment per task)

    assignment = Assignment(
        task_id=task.id, worker_id=request.worker_id, source=AssignmentSource.supervisor, assigned_at=now
    )
    session.add(assignment)
    session.flush()

    order_run_id = session.scalar(select(Order.run_id).where(Order.id == task.order_id))
    if was_stuck:
        resolved = session.execute(
            update(TaskException)
            .where(TaskException.task_id == task.id, TaskException.resolved_at.is_(None))
            .values(resolved_at=now)
            .execution_options(synchronize_session=False)
        )
        if resolved.rowcount > 0:
            session.add(
                Event(event_type="exception_resolved", run_id=order_run_id, order_id=task.order_id, task_id=task.id)
            )
    session.add(
        Event(
            event_type="task_reassigned" if previous is not None else "task_assigned",
            run_id=order_run_id,
            order_id=task.order_id,
            task_id=task.id,
            worker_id=request.worker_id,
            assignment_id=assignment.id,
            payload={
                "source": "supervisor",
                "reason": request.reason,
                "previous_assignment_id": previous.id if previous is not None else None,
                "previous_worker_id": previous.worker_id if previous is not None else None,
            },
        )
    )

    return ReassignResult(
        task_id=task.id,
        status=task.status,
        version=task.version,
        assignment=NewAssignmentOut(
            assignment_id=assignment.id,
            worker_id=assignment.worker_id,
            source=assignment.source,
            assigned_at=assignment.assigned_at,
        ),
        previous_assignment=(
            PreviousAssignmentOut(
                assignment_id=previous.id,
                worker_id=previous.worker_id,
                outcome=previous.outcome,
                ended_at=previous.ended_at,
            )
            if previous is not None
            else None
        ),
    )

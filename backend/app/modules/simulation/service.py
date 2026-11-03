"""Exception handling, bin rerouting and simulation state changes.

This is the business logic behind the simulation endpoints. Routers call these functions;
nothing here knows about HTTP except ApiError, which carries the status code to return.

Three rules run through every function:
1. One transaction per action. Each public function either commits all of its changes or,
   if anything fails, rolls all of them back. The database is never left half-updated.
2. Compare-and-set on version. Every update says "UPDATE ... WHERE id = :id AND version = :seen"
   and bumps version. If zero rows change, someone else updated the row first -> 409 Conflict.
3. Reservations. A task's qty is "reserved" in its bin, so two tasks never count on the same units.
"""
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.database import utcnow
# ApiError(status, message, code) becomes the JSON error response {"detail": ..., "code": ...}.
from app.core.errors import ApiError
from app.modules.assignment.models import Assignment
# Module import, not `from ... import name`: events.service imports simulation.models, and this
# form still works while that module is mid-import (it avoids a circular-import error).
from app.modules.events import service as events
from app.modules.orders.models import Order
from app.modules.simulation.models import Inventory, Location, SimRun, Sku, TaskException
from app.modules.simulation.schemas import ExceptionCreate
from app.modules.tasks.models import Task
from app.modules.workforce.models import Worker


# Small containers for what the service hands back to the router.
@dataclass
class PickResult:
    task: Task
    assignment: Assignment
    order: Order
    picked_at: datetime


@dataclass
class ExceptionResult:
    exception: TaskException
    task_status: str


# ---------------------------------------------------------------------------------------------
# Building blocks used by the public functions below
# ---------------------------------------------------------------------------------------------


def _compare_and_set(db: Session, model, row, *conditions, **values) -> None:
    """Update `row` only if its version (and any extra conditions) still match what we read.

    model: the table class (Task, Worker, ...). row: the object we loaded earlier.
    conditions: extra WHERE rules, e.g. Task.status == "assigned".
    values: the columns to change, e.g. status="open".
    """
    result = db.execute(
        update(model)
        # Only touch this row, and only if nobody changed it since we read it.
        .where(model.id == row.id, model.version == row.version, *conditions)
        # Apply the changes and bump the version so the next reader sees it changed.
        .values(version=model.version + 1, **values)
        # Don't try to patch our in-memory copy; we expire it below instead.
        .execution_options(synchronize_session=False)
    )
    # rowcount = how many rows the UPDATE changed. Anything but 1 means we lost a race.
    if result.rowcount != 1:
        raise ApiError(409, f"{model.__name__} {row.id} was changed by another request", "version_conflict")
    # The UPDATE bypassed the ORM; reload the row on next access so callers never read stale values.
    db.expire(row)


def _inventory_row(db: Session, sku_id: int, location_id: int) -> Inventory | None:
    """The inventory row for one SKU in one bin, locked until the transaction ends (or None)."""
    return db.scalar(
        select(Inventory)
        .where(Inventory.sku_id == sku_id, Inventory.location_id == location_id)
        # SELECT ... FOR UPDATE: on MySQL, other transactions must wait to change this row.
        .with_for_update()
    )


def _release(db: Session, task: Task, *, on_hand: int | None = None) -> None:
    """Drop the task's reservation in its current bin; optionally correct the bin's on_hand."""
    row = _inventory_row(db, task.sku_id, task.location_id)
    # No inventory row for this SKU/bin: nothing to release.
    if row is None:
        return
    # Give back the units this task had reserved. max(..., 0) guards against going negative.
    values = {"reserved": max(row.reserved - task.qty, 0)}
    # For a stockout, the picker counted what's really there; make the system agree.
    if on_hand is not None:
        values["on_hand"] = on_hand
    _compare_and_set(db, Inventory, row, **values)


def _reserve_nearest_bin(db: Session, task: Task) -> int | None:
    """Reserve task.qty in the closest other bin with enough unreserved stock. Returns its location id."""
    # The bin the task is moving away from.
    origin = db.get(Location, task.location_id)
    # Manhattan distance from that bin: |dx| + |dy|, i.e. walking on a grid with no diagonals.
    distance = func.abs(Location.x - origin.x) + func.abs(Location.y - origin.y)
    # Free stock = what's there minus what's already promised.
    available = Inventory.on_hand - Inventory.reserved
    candidate = db.scalar(
        select(Inventory)
        # Join to locations so we can sort by the bin's coordinates.
        .join(Location, Inventory.location_id == Location.id)
        .where(
            Inventory.sku_id == task.sku_id,             # same product
            Inventory.location_id != task.location_id,   # a different bin than the failed one
            available >= task.qty,                       # with enough free stock for the whole task
        )
        # Nearest first; Inventory.id breaks ties so the choice is always the same.
        .order_by(distance, Inventory.id)
        .limit(1)
        # Lock just the inventory row we pick.
        .with_for_update(of=Inventory)
    )
    # No bin qualifies: the caller will put the task into "exception".
    if candidate is None:
        return None
    # Reserve the units, re-checking there's still enough free stock at the moment of the update.
    _compare_and_set(db, Inventory, candidate, available >= task.qty, reserved=candidate.reserved + task.qty)
    return candidate.location_id


def _load_active_assignment(db: Session, task_id: int, assignment_id: int) -> tuple[Task, Assignment, Worker]:
    """Lock the task, its assignment and worker; 404/422/409 unless the assignment is the task's active one."""
    # Load and lock the task.
    task = db.get(Task, task_id, with_for_update=True)
    if task is None:
        raise ApiError(404, f"Task {task_id} not found", "task_not_found")
    # Load and lock the assignment.
    assignment = db.get(Assignment, assignment_id, with_for_update=True)
    if assignment is None:
        raise ApiError(404, f"Assignment {assignment_id} not found", "assignment_not_found")
    # The caller passed an assignment that belongs to some other task: bad input.
    if assignment.task_id != task.id:
        raise ApiError(422, f"Assignment {assignment.id} is not for task {task.id}", "assignment_mismatch")
    # The assignment already ended, or the task isn't in progress: the state has moved on.
    if assignment.ended_at is not None or task.status != "assigned":
        raise ApiError(
            409,
            f"Task {task.id} is '{task.status}' and assignment {assignment.id} is "
            f"{'closed' if assignment.ended_at else 'active'}; only an active assignment can change it",
            "state_conflict",
        )
    # Load and lock the worker doing the assignment.
    worker = db.get(Worker, assignment.worker_id, with_for_update=True)
    return task, assignment, worker


# ---------------------------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------------------------


def list_exceptions(db: Session, *, open_only: bool | None, limit: int) -> list[tuple[TaskException, Task]]:
    """Exceptions with their task, newest first. open_only=True: unresolved; False: resolved; None: all."""
    # Each result row is (exception, its task), so the router can show the task's current status.
    query = select(TaskException, Task).join(Task, TaskException.task_id == Task.id)
    if open_only is True:
        # Unresolved = no resolved_at yet = waiting for the supervisor.
        query = query.where(TaskException.resolved_at.is_(None))
    elif open_only is False:
        query = query.where(TaskException.resolved_at.is_not(None))
    # Newest first, capped at `limit` rows.
    return list(db.execute(query.order_by(TaskException.opened_at.desc(), TaskException.id.desc()).limit(limit)))


def open_exception(db: Session, task_id: int, data: ExceptionCreate) -> ExceptionResult:
    """Record an exception against an active assignment and recover the task, all in one transaction.

    - stockout: bin on_hand is corrected to qty_found, reservation released, task rerouted.
    - jam: reservation released, task rerouted to another bin.
    - worker_down: worker goes 'down'; the bin is fine, so the task reopens in place.
    A task with no bin to reroute to becomes 'exception' and waits for the supervisor. Every other
    case is handled here, so the exception is recorded already resolved and never shows as open.
    """
    try:
        result = _open_exception(db, task_id, data)
    except Exception:
        # Anything went wrong (including a 409/404/422 we raised): undo every change.
        db.rollback()
        raise
    # Everything succeeded: save all the changes together.
    db.commit()
    return result


def _open_exception(db: Session, task_id: int, data: ExceptionCreate) -> ExceptionResult:
    # Validate and lock the task, assignment and worker (raises 404/422/409 if something's off).
    task, assignment, worker = _load_active_assignment(db, task_id, data.assignment_id)
    # A "stockout" where the picker found enough units isn't a stockout.
    if data.type == "stockout" and data.qty_found >= task.qty:
        raise ApiError(422, f"qty_found must be below the task qty ({task.qty}) for a stockout", "invalid_qty_found")

    # Remember the "before" values; the rows get reloaded after each update.
    now = utcnow()
    from_location_id = task.location_id
    previous_worker_status = worker.status
    rerouted_to = None

    if data.type == "worker_down":
        # The bin is fine; only the worker is out. Keep the reservation, reopen the task in place,
        # and park the worker as "down" so the assigner skips them until they recover.
        new_status, worker_status = "open", "down"
    else:
        # stockout or jam: the bin can't fill this task. Release its reservation there
        # (for a stockout, also correct on_hand to what the picker found)...
        _release(db, task, on_hand=data.qty_found if data.type == "stockout" else None)
        # ...and try to reserve the stock in the nearest other bin.
        rerouted_to = _reserve_nearest_bin(db, task)
        # Found a bin: the task goes back to "open" for the assigner. No bin: "exception" for the
        # supervisor. Either way the worker is free again.
        new_status, worker_status = ("open" if rerouted_to else "exception"), "idle"

    # Update the task: new status, and the new bin if it was rerouted (otherwise keep the old one).
    # Task.status == "assigned" re-checks that nothing moved the task since we loaded it.
    _compare_and_set(
        db, Task, task, Task.status == "assigned",
        status=new_status, location_id=rerouted_to or from_location_id, updated_at=now,
    )
    # Close the assignment as failed. ended_at IS NULL re-checks that it was still open.
    _compare_and_set(db, Assignment, assignment, Assignment.ended_at.is_(None), ended_at=now, outcome="failed")
    # Set the worker to idle (or down).
    _compare_and_set(db, Worker, worker, status=worker_status)

    # Record the exception itself.
    run_id = events.active_run_id(db)
    exception = TaskException(
        run_id=run_id,
        type=data.type,
        task_id=task.id,
        assignment_id=assignment.id,
        qty_found=data.qty_found,
        from_location_id=from_location_id,
        rerouted_to_location_id=rerouted_to,
        opened_at=now,
        # Handled automatically (rerouted or reopened) -> resolved now. Stuck -> left open.
        resolved_at=None if new_status == "exception" else now,
    )
    db.add(exception)
    # flush sends the INSERT now (still inside the transaction) so exception.id gets a value.
    db.flush()

    # Write the events, in the same transaction as the changes they describe.
    ids = {"run_id": run_id, "order_id": task.order_id, "task_id": task.id}
    events.record_event(
        db, "exception_opened", **ids, worker_id=worker.id, assignment_id=assignment.id,
        payload={"exception_id": exception.id, "type": data.type, "qty_found": data.qty_found},
    )
    # Only log a worker status change if the status actually changed.
    if previous_worker_status != worker_status:
        events.record_event(db, "worker_status_changed", run_id=run_id, worker_id=worker.id,
                     payload={"from": previous_worker_status, "to": worker_status})
    # One event describing what happened to the task.
    if rerouted_to:
        events.record_event(db, "task_rerouted", **ids, payload={"from_location_id": from_location_id, "to_location_id": rerouted_to})
    elif new_status == "exception":
        events.record_event(db, "task_exception", **ids, payload={"exception_id": exception.id})
    else:
        events.record_event(db, "task_reopened", **ids, payload={"location_id": from_location_id})

    return ExceptionResult(exception=exception, task_status=new_status)


# ---------------------------------------------------------------------------------------------
# Picks
# ---------------------------------------------------------------------------------------------


def pick_task(db: Session, task_id: int, assignment_id: int) -> PickResult:
    """Complete a pick: take stock out of the bin, close the assignment, free the worker at the bin.

    If that was the order's last outstanding task, the order and all its tasks move to 'complete'.
    """
    # Same all-or-nothing pattern as open_exception.
    try:
        result = _pick_task(db, task_id, assignment_id)
    except Exception:
        db.rollback()
        raise
    db.commit()
    return result


def _pick_task(db: Session, task_id: int, assignment_id: int) -> PickResult:
    # Validate and lock the task, assignment and worker.
    task, assignment, worker = _load_active_assignment(db, task_id, assignment_id)
    now = utcnow()
    run_id = events.active_run_id(db)
    # Copy these out now; the task row is reloaded after it's updated.
    qty, location_id, order_id = task.qty, task.location_id, task.order_id

    # The bin must physically hold enough units. If not, the caller should raise a stockout instead.
    stock = _inventory_row(db, task.sku_id, location_id)
    if stock is None or stock.on_hand < qty:
        raise ApiError(
            409, f"Bin {location_id} has {stock.on_hand if stock else 0} on hand, task needs {qty}; raise a stockout",
            "insufficient_stock",
        )
    # Take the units out of the bin and release the reservation they were held under.
    _compare_and_set(
        db, Inventory, stock, Inventory.on_hand >= qty,
        on_hand=stock.on_hand - qty, reserved=max(stock.reserved - qty, 0),
    )
    # The bin's coordinates: the worker is standing there after the pick.
    location = db.get(Location, location_id)
    # Task: assigned -> picked.
    _compare_and_set(db, Task, task, Task.status == "assigned", status="picked", updated_at=now)
    # Assignment: closed as completed.
    _compare_and_set(db, Assignment, assignment, Assignment.ended_at.is_(None), ended_at=now, outcome="completed")
    previous_worker_status = worker.status
    # Worker: free again, and moved to the bin's position (that's where the next walk starts from).
    _compare_and_set(db, Worker, worker, status="idle", x=location.x, y=location.y)

    # Log the pick. Throughput counts these events.
    events.record_event(
        db, "task_picked", run_id=run_id, order_id=order_id, task_id=task_id, worker_id=worker.id,
        assignment_id=assignment.id, payload={"qty": qty, "location_id": location_id},
    )
    if previous_worker_status != "idle":
        events.record_event(db, "worker_status_changed", run_id=run_id, worker_id=worker.id,
                     payload={"from": previous_worker_status, "to": "idle"})

    # Is the order finished? Count its tasks that are not yet picked/complete.
    order = db.get(Order, order_id, with_for_update=True)
    outstanding = db.scalar(
        select(func.count()).select_from(Task).where(Task.order_id == order_id, Task.status.not_in(("picked", "complete")))
    )
    if outstanding == 0 and order.status != "complete":
        # Every task is picked: complete the order...
        _compare_and_set(db, Order, order, Order.status != "complete", status="complete", completed_at=now)
        # ...and move all of its picked tasks to "complete" in one statement (bumping each version).
        db.execute(
            update(Task)
            .where(Task.order_id == order_id, Task.status == "picked")
            .values(status="complete", version=Task.version + 1, updated_at=now)
            .execution_options(synchronize_session=False)
        )
        events.record_event(db, "order_completed", run_id=run_id, order_id=order_id)

    # Push pending changes to the DB, then forget cached rows so the result reflects the new state.
    db.flush()
    db.expire_all()
    return PickResult(task=db.get(Task, task_id), assignment=assignment, order=order, picked_at=now)


# ---------------------------------------------------------------------------------------------
# Runs, simulator reads, and worker recovery
# ---------------------------------------------------------------------------------------------


def active_run(db: Session) -> SimRun:
    """The newest run that hasn't ended, or 404."""
    run = db.scalar(select(SimRun).where(SimRun.ended_at.is_(None)).order_by(SimRun.id.desc()).limit(1))
    if run is None:
        raise ApiError(404, "No simulation run is active", "no_active_run")
    return run


def start_run(db: Session, seed: int | None, config: dict | None) -> SimRun:
    """End any open runs and start a new one, so events always belong to exactly one run."""
    now = utcnow()
    # Close every run that's still open.
    db.execute(update(SimRun).where(SimRun.ended_at.is_(None)).values(ended_at=now))
    # Open the new one.
    run = SimRun(seed=seed, config=config, started_at=now)
    db.add(run)
    db.commit()
    return run


def active_assignments(db: Session) -> list:
    """Every assignment still in progress, with the worker, task, bin, SKU and bin stock in one query.

    Each row is (Assignment, Task, Worker, Location, sku_code, on_hand).
    """
    return list(db.execute(
        select(Assignment, Task, Worker, Location, Sku.sku_code, func.coalesce(Inventory.on_hand, 0))
        .join(Task, Assignment.task_id == Task.id)          # the task being worked on
        .join(Worker, Assignment.worker_id == Worker.id)    # who is doing it
        .join(Location, Task.location_id == Location.id)    # the bin they're going to
        .join(Sku, Task.sku_id == Sku.id)                   # the product's code
        # outerjoin: still return the row even if the bin has no inventory row (on_hand -> 0 via coalesce).
        .outerjoin(Inventory, (Inventory.sku_id == Task.sku_id) & (Inventory.location_id == Task.location_id))
        # Active = not ended yet.
        .where(Assignment.ended_at.is_(None))
        .order_by(Assignment.id)
    ))


def available_skus(db: Session) -> list:
    """(sku_code, total free stock) for every SKU with free stock in at least one bin."""
    # Free stock summed over all of the SKU's bins.
    available = func.sum(Inventory.on_hand - Inventory.reserved)
    return list(db.execute(
        select(Sku.sku_code, available)
        .join(Inventory, Inventory.sku_id == Sku.id)
        .group_by(Sku.sku_code)
        # HAVING filters after grouping: only SKUs with something left.
        .having(available > 0)
        .order_by(Sku.sku_code)
    ))


def recover_worker(db: Session, worker_id: int) -> Worker:
    """Bring a 'down' worker back to 'idle' so the assigner can use them again."""
    worker = db.get(Worker, worker_id, with_for_update=True)
    if worker is None:
        raise ApiError(404, f"Worker {worker_id} not found", "worker_not_found")
    # Only a downed worker can recover.
    if worker.status != "down":
        raise ApiError(409, f"Worker {worker_id} is '{worker.status}', not 'down'", "state_conflict")
    try:
        _compare_and_set(db, Worker, worker, Worker.status == "down", status="idle")
        events.record_event(db, "worker_status_changed", worker_id=worker_id, payload={"from": "down", "to": "idle"})
    except Exception:
        db.rollback()
        raise
    db.commit()
    return worker

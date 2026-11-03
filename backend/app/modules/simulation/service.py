"""What happens when a worker finishes an assignment.

Each public function commits all of its changes together or rolls all of them back, so the
database is never left half-updated. Task status changes go through tasks.service.transition().
"""
from datetime import datetime

from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.errors import ApiError
from app.modules.assignment.models import Assignment, AssignmentOutcome
from app.modules.events.models import Event
from app.modules.orders.models import Order, OrderStatus
from app.modules.simulation.models import ExceptionType, TaskException
from app.modules.simulation.schemas import (
    ExceptionCreate,
    ExceptionListItem,
    ExceptionListOut,
    ExceptionOut,
    PickOut,
    WorkerRecoveredOut,
)
from app.modules.tasks.models import Task, TaskStatus
from app.modules.tasks.service import transition
from app.modules.warehouse.models import Inventory, Location
from app.modules.workforce.models import Worker, WorkerStatus


def pick_task(session: Session, task_id: int, assignment_id: int) -> PickOut:
    """Complete a pick: remove the stock, close the assignment, and free the worker at the bin.

    Picking an order's last unpicked task also completes the order. Raises 404 for an unknown
    task or assignment, 422 if the assignment belongs to another task, and 409 if the assignment
    has ended, the task isn't assigned, or the bin doesn't hold enough stock.
    """
    try:
        result = _pick_task(session, task_id, assignment_id)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return result


def _lock_order_and_load(session: Session, task_id: int, assignment_id: int) -> tuple[Order, Task, Assignment]:
    """Lock the task's order, then load the task and its still-active assignment, or raise."""
    order_id = session.scalar(select(Task.order_id).where(Task.id == task_id))
    if order_id is None:
        raise ApiError(404, "task_not_found", f"Task {task_id} not found")

    # Lock the order before anything else, so work on one order runs one at a time. Expedite also
    # locks the order before its tasks, so the two can't deadlock. The rollback ends the snapshot
    # the read above opened. Without it, the unpicked count in a pick could miss a pick that
    # committed while this one waited for the lock: two simultaneous last picks would each see the
    # other's task as unpicked, and the order would never complete.
    session.rollback()
    order = session.scalar(select(Order).where(Order.id == order_id).with_for_update())

    task = session.get(Task, task_id)
    assignment = session.get(Assignment, assignment_id)
    if assignment is None:
        raise ApiError(404, "assignment_not_found", f"Assignment {assignment_id} not found")
    if assignment.task_id != task.id:
        raise ApiError(422, "assignment_mismatch", f"Assignment {assignment_id} is not for task {task_id}")
    if assignment.ended_at is not None:
        raise ApiError(409, "assignment_not_active", f"Assignment {assignment_id} has already ended")
    return order, task, assignment


def _close_assignment(session: Session, assignment_id: int, outcome: AssignmentOutcome, now: datetime) -> None:
    closed = session.execute(
        update(Assignment)
        .where(Assignment.id == assignment_id, Assignment.ended_at.is_(None))
        .values(ended_at=now, outcome=outcome)
        .execution_options(synchronize_session=False)
    )
    if closed.rowcount != 1:
        raise ApiError(409, "assignment_not_active", f"Assignment {assignment_id} has already ended")


def _pick_task(session: Session, task_id: int, assignment_id: int) -> PickOut:
    order, task, assignment = _lock_order_and_load(session, task_id, assignment_id)
    now = utcnow()
    order_id, worker_id, qty, location_id = order.id, assignment.worker_id, task.qty, task.location_id
    transition(session, task, task.status, TaskStatus.picked)
    _close_assignment(session, assignment_id, AssignmentOutcome.completed, now)

    _remove_stock(session, task, qty, location_id)
    order_status = _complete_order_if_finished(session, order, now)
    worker_freed = _free_worker_at_bin(session, worker_id, location_id)

    session.add(
        Event(
            event_type="task_picked",
            run_id=order.run_id,
            order_id=order_id,
            task_id=task_id,
            worker_id=worker_id,
            assignment_id=assignment_id,
            payload={"qty": qty, "location_id": location_id},
        )
    )
    if worker_freed:
        session.add(
            Event(
                event_type="worker_status_changed",
                run_id=order.run_id,
                worker_id=worker_id,
                payload={"from": WorkerStatus.busy.value, "to": WorkerStatus.idle.value},
            )
        )
    if order_status is OrderStatus.complete:
        session.add(Event(event_type="order_completed", run_id=order.run_id, order_id=order_id))

    return PickOut(
        task_id=task_id,
        status=task.status,
        version=task.version,
        assignment_id=assignment_id,
        worker_id=worker_id,
        order_id=order_id,
        order_status=order_status,
        picked_at=now,
    )


def _remove_stock(session: Session, task: Task, qty: int, location_id: int) -> None:
    """Take qty out of the bin and drop the reservation it was held under, or raise a 409.

    Both columns are unsigned, so MySQL errors on a subtraction below zero. A task can reach this
    point holding no reservation, so the CASE stops at zero.
    """
    removed = session.execute(
        update(Inventory)
        .where(Inventory.sku_id == task.sku_id, Inventory.location_id == location_id, Inventory.qty_on_hand >= qty)
        .values(
            qty_on_hand=Inventory.qty_on_hand - qty,
            qty_reserved=case((Inventory.qty_reserved >= qty, Inventory.qty_reserved - qty), else_=0),
        )
        .execution_options(synchronize_session=False)
    )
    if removed.rowcount != 1:
        raise ApiError(409, "insufficient_stock", f"Bin {location_id} holds fewer than {qty}; raise a stockout instead")


def _complete_order_if_finished(session: Session, order: Order, now: datetime) -> OrderStatus:
    """Complete the order if every task is picked. The caller holds the order's lock."""
    unpicked = session.scalar(
        select(func.count()).select_from(Task).where(Task.order_id == order.id, Task.status != TaskStatus.picked)
    )
    if unpicked > 0 or order.status is OrderStatus.complete:
        return order.status
    session.execute(
        update(Order)
        .where(Order.id == order.id)
        .values(status=OrderStatus.complete, completed_at=now, version=Order.version + 1)
        .execution_options(synchronize_session=False)
    )
    return OrderStatus.complete


def _free_worker_at_bin(session: Session, worker_id: int, location_id: int) -> bool:
    """Move the worker to the bin, and make them idle if busy. Returns whether they were freed.

    A worker someone marked down meanwhile stays down. workers.version isn't bumped, because it
    guards supervisors' edits (PATCH), and those shouldn't conflict with routine work.
    """
    location = session.get(Location, location_id)
    session.execute(
        update(Worker)
        .where(Worker.id == worker_id)
        .values(x=location.x, y=location.y)
        .execution_options(synchronize_session=False)
    )
    return _free_worker(session, worker_id)


def _free_worker(session: Session, worker_id: int) -> bool:
    freed = session.execute(
        update(Worker)
        .where(Worker.id == worker_id, Worker.status == WorkerStatus.busy)
        .values(status=WorkerStatus.idle)
        .execution_options(synchronize_session=False)
    )
    return freed.rowcount == 1


def open_exception(session: Session, task_id: int, data: ExceptionCreate) -> ExceptionOut:
    """Record an exception against an active assignment and recover the task.

    - stockout: the bin's stock is corrected to qty_found and the task moves to the nearest other
      bin that can cover it.
    - jam: the task moves the same way, and the bin's stock is left alone.
    - worker_down: the worker goes down. The bin is fine, so the task reopens in place and keeps
      its reservation.

    A task with no bin to move to becomes 'exception' and waits for the supervisor, which is the
    only case that leaves the exception open. Raises 404 for an unknown task or assignment, 422
    for bad input, and 409 if the assignment has ended or the task isn't assigned.
    """
    try:
        result = _open_exception(session, task_id, data)
        session.commit()
    except Exception:
        session.rollback()
        raise
    return result


def _open_exception(session: Session, task_id: int, data: ExceptionCreate) -> ExceptionOut:
    order, task, assignment = _lock_order_and_load(session, task_id, data.assignment_id)
    if data.type is ExceptionType.stockout and data.qty_found >= task.qty:
        raise ApiError(422, "invalid_qty_found", f"qty_found must be below the task qty ({task.qty}) for a stockout")

    now = utcnow()
    order_id, run_id, worker_id, from_location_id = order.id, order.run_id, assignment.worker_id, task.location_id
    assignment_id = assignment.id
    rerouted_to = None
    if data.type is ExceptionType.worker_down:
        new_status = TaskStatus.open
    else:
        qty_found = data.qty_found if data.type is ExceptionType.stockout else None
        rerouted_to = _release_and_reroute(session, task, qty_found)
        new_status = TaskStatus.open if rerouted_to is not None else TaskStatus.exception

    transition(session, task, TaskStatus.assigned, new_status)
    if rerouted_to is not None:
        session.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(location_id=rerouted_to)
            .execution_options(synchronize_session=False)
        )
    _close_assignment(session, assignment_id, AssignmentOutcome.failed, now)
    worker_change = _update_worker_after_exception(session, worker_id, data.type)

    exception = TaskException(
        task_id=task_id,
        assignment_id=assignment_id,
        run_id=run_id,
        type=data.type,
        qty_found=data.qty_found,
        from_location_id=from_location_id,
        rerouted_to_location_id=rerouted_to,
        opened_at=now,
        resolved_at=None if new_status is TaskStatus.exception else now,
    )
    session.add(exception)
    session.flush()  # assigns exception.id, needed for the events

    ids = {"run_id": run_id, "order_id": order_id, "task_id": task_id}
    session.add(
        Event(
            event_type="exception_opened",
            worker_id=worker_id,
            assignment_id=assignment_id,
            payload={"exception_id": exception.id, "type": data.type.value, "qty_found": data.qty_found},
            **ids,
        )
    )
    if worker_change is not None:
        session.add(
            Event(
                event_type="worker_status_changed",
                run_id=run_id,
                worker_id=worker_id,
                payload={"from": worker_change[0].value, "to": worker_change[1].value},
            )
        )
    if rerouted_to is not None:
        payload = {"from_location_id": from_location_id, "to_location_id": rerouted_to}
        session.add(Event(event_type="task_rerouted", payload=payload, **ids))
    elif new_status is TaskStatus.exception:
        session.add(Event(event_type="task_exception", payload={"exception_id": exception.id}, **ids))
    else:
        session.add(Event(event_type="task_reopened", payload={"location_id": from_location_id}, **ids))

    return ExceptionOut(
        exception_id=exception.id,
        type=exception.type,
        task_id=task_id,
        opened_at=now,
        task_status=new_status,
        rerouted_to_location_id=rerouted_to,
    )


def _release_and_reroute(session: Session, task: Task, qty_found: int | None) -> int | None:
    """Release the task's reservation, then reserve it in the nearest bin that can cover it all.

    Returns that bin's id, or None if no other bin can. The SKU's rows stay locked until commit, in
    the same order intake locks them, so the two can't deadlock or over-reserve. The stock math
    stays in Python because a stockout can leave a bin with more reserved than on hand, and MySQL
    errors when a subtraction of unsigned columns goes below zero.
    """
    rows = session.execute(
        select(Inventory, Location)
        .join(Location, Location.id == Inventory.location_id)
        .where(Inventory.sku_id == task.sku_id)
        .order_by(Inventory.location_id)
        .with_for_update(of=Inventory)
    ).all()

    origin = session.get(Location, task.location_id)
    for row, _ in rows:
        if row.location_id == task.location_id:
            row.qty_reserved = max(row.qty_reserved - task.qty, 0)
            if qty_found is not None:
                row.qty_on_hand = qty_found

    candidates = [
        (abs(location.x - origin.x) + abs(location.y - origin.y), row.location_id, row)
        for row, location in rows
        if row.location_id != task.location_id and row.qty_on_hand - row.qty_reserved >= task.qty
    ]
    if not candidates:
        return None
    _, location_id, nearest = min(candidates, key=lambda candidate: candidate[:2])
    nearest.qty_reserved += task.qty
    return location_id


def _update_worker_after_exception(
    session: Session, worker_id: int, exception_type: ExceptionType
) -> tuple[WorkerStatus, WorkerStatus] | None:
    """Free the worker, or mark them down. Returns (from, to) if their status changed."""
    if exception_type is not ExceptionType.worker_down:
        return (WorkerStatus.busy, WorkerStatus.idle) if _free_worker(session, worker_id) else None

    previous = session.scalar(select(Worker.status).where(Worker.id == worker_id).with_for_update())
    if previous is WorkerStatus.down:
        return None
    session.execute(
        update(Worker)
        .where(Worker.id == worker_id)
        .values(status=WorkerStatus.down)
        .execution_options(synchronize_session=False)
    )
    return previous, WorkerStatus.down


def list_exceptions(session: Session, only_open: bool | None, limit: int) -> ExceptionListOut:
    """Exceptions newest first. only_open: True for unresolved, False for resolved, None for all."""
    query = select(TaskException, Task.order_id, Task.status).join(Task, Task.id == TaskException.task_id)
    if only_open is True:
        query = query.where(TaskException.resolved_at.is_(None))
    elif only_open is False:
        query = query.where(TaskException.resolved_at.is_not(None))
    rows = session.execute(query.order_by(TaskException.opened_at.desc(), TaskException.id.desc()).limit(limit))
    items = [
        ExceptionListItem(
            exception_id=exception.id,
            type=exception.type,
            task_id=exception.task_id,
            order_id=order_id,
            assignment_id=exception.assignment_id,
            qty_found=exception.qty_found,
            from_location_id=exception.from_location_id,
            rerouted_to_location_id=exception.rerouted_to_location_id,
            task_status=task_status,
            opened_at=exception.opened_at,
            resolved_at=exception.resolved_at,
        )
        for exception, order_id, task_status in rows
    ]
    return ExceptionListOut(items=items, count=len(items))


def recover_worker(session: Session, worker_id: int) -> WorkerRecoveredOut:
    """Bring a down worker back to idle. Raises 404 if unknown, 409 if they aren't down."""
    try:
        recovered = session.execute(
            update(Worker)
            .where(Worker.id == worker_id, Worker.status == WorkerStatus.down)
            .values(status=WorkerStatus.idle)
            .execution_options(synchronize_session=False)
        )
        if recovered.rowcount != 1:
            worker = session.get(Worker, worker_id)
            if worker is None:
                raise ApiError(404, "worker_not_found", f"Worker {worker_id} not found")
            raise ApiError(409, "worker_not_down", f"Worker {worker_id} is {worker.status.value}, not down")
        session.add(
            Event(
                event_type="worker_status_changed",
                worker_id=worker_id,
                payload={"from": WorkerStatus.down.value, "to": WorkerStatus.idle.value},
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    return WorkerRecoveredOut(worker_id=worker_id, status=WorkerStatus.idle)

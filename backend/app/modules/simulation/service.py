"""What happens when a worker finishes an assignment.

Each public function commits all of its changes together or rolls all of them back, so the
database is never left half-updated. Task status changes go through tasks.service.transition().
"""
from sqlalchemy import case, func, select, update
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.errors import ApiError
from app.modules.assignment.models import Assignment, AssignmentOutcome
from app.modules.events.models import Event
from app.modules.orders.models import Order, OrderStatus
from app.modules.simulation.schemas import PickOut
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


def _pick_task(session: Session, task_id: int, assignment_id: int) -> PickOut:
    order_id = session.scalar(select(Task.order_id).where(Task.id == task_id))
    if order_id is None:
        raise ApiError(404, "task_not_found", f"Task {task_id} not found")

    # Lock the order before anything else, so picks on one order run one at a time. Expedite also
    # locks the order before its tasks, so the two can't deadlock. The rollback ends the snapshot
    # the read above opened. Without it, the unpicked count below could miss a pick that committed
    # while this one waited for the lock: two simultaneous last picks would each see the other's
    # task as unpicked, and the order would never complete.
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

    now = utcnow()
    worker_id, qty, location_id = assignment.worker_id, task.qty, task.location_id
    transition(session, task, task.status, TaskStatus.picked)
    closed = session.execute(
        update(Assignment)
        .where(Assignment.id == assignment_id, Assignment.ended_at.is_(None))
        .values(ended_at=now, outcome=AssignmentOutcome.completed)
        .execution_options(synchronize_session=False)
    )
    if closed.rowcount != 1:
        raise ApiError(409, "assignment_not_active", f"Assignment {assignment_id} has already ended")

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


def _complete_order_if_finished(session: Session, order: Order, now) -> OrderStatus:
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
    freed = session.execute(
        update(Worker)
        .where(Worker.id == worker_id, Worker.status == WorkerStatus.busy)
        .values(status=WorkerStatus.idle)
        .execution_options(synchronize_session=False)
    )
    return freed.rowcount == 1

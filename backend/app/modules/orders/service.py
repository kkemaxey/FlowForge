"""Order intake: write the order and its lines, turn each line into pick tasks, reserve stock.

Everything for one order (order, lines, tasks, reservations, events) commits in one
transaction, so a failure anywhere leaves nothing behind.
"""
from collections import defaultdict
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import utcnow
from app.core.errors import ApiError
from app.modules.events.models import Event
from app.modules.orders.models import Order, OrderLine, OrderStatus
from app.modules.orders.schemas import OrderCreate, OrderLineOut, OrderListOut, OrderOut, OrderTaskOut
from app.modules.simulation.models import SimRun
from app.modules.tasks.models import Task, TaskStatus
from app.modules.warehouse.models import Inventory, Location, Sku
from app.modules.warehouse.schemas import LocationOut

# Expedited work sorts ahead of everything else in the queue: intake priorities are capped at 100.
EXPEDITE_PRIORITY = 110


class InsufficientStock(ApiError):
    """409: a line asks for more of a SKU than is unreserved across all its bins."""

    def __init__(self, sku_code: str, requested: int, available: int) -> None:
        super().__init__(
            409,
            "insufficient_stock",
            f"{sku_code}: {requested} requested but only {available} unreserved across all bins",
        )
        self.sku_code = sku_code
        self.available = available


def create_order(session: Session, payload: OrderCreate) -> tuple[Order, bool]:
    """Intake one order. Returns (order, created); created is False for a replayed external_ref."""
    existing = _find_by_ref(session, payload.external_ref)
    if existing is not None:
        return existing, False

    try:
        order = _intake(session, payload)
        session.commit()
    except IntegrityError:
        session.rollback()
        # An identical request committed between our check and our insert: treat it as a replay.
        existing = _find_by_ref(session, payload.external_ref)
        if existing is not None:
            return existing, False
        raise
    except Exception:
        session.rollback()
        raise
    return order, True


def get_order(session: Session, order_id: int) -> Order:
    order = session.get(Order, order_id)
    if order is None:
        raise ApiError(404, "order_not_found", f"Order {order_id} not found")
    return order


def expedite_order(session: Session, order_id: int) -> Order:
    """Mark the order expedited and move its unfinished tasks to the front of the queue.

    Raises the priority of every task not yet picked (not only open ones), so a task that is
    assigned now but later sent back to the queue (stockout reroute, worker down) keeps its place.
    This only reorders the queue: greedy_v1 pairs by distance and ignores priority. Expediting an
    already-expedited order is a no-op that returns it unchanged.
    """
    try:
        order = get_order(session, order_id)
        if order.status is OrderStatus.complete:
            raise ApiError(409, "order_complete", f"Order {order_id} is already complete")
        if order.expedited:
            return order

        marked = session.execute(
            update(Order)
            .where(Order.id == order.id, Order.version == order.version, Order.status == OrderStatus.open)
            .values(expedited=True, priority=EXPEDITE_PRIORITY, version=Order.version + 1)
            .execution_options(synchronize_session=False)
        )
        if marked.rowcount != 1:
            raise ApiError(409, "version_conflict", f"Order {order_id} changed while expediting; reload and retry")

        raised = session.execute(
            update(Task)
            .where(Task.order_id == order.id, Task.status != TaskStatus.picked)
            .values(priority=EXPEDITE_PRIORITY, updated_at=utcnow())
            .execution_options(synchronize_session=False)
        )
        session.add(
            Event(
                event_type="order_expedited",
                run_id=order.run_id,
                order_id=order.id,
                payload={"priority": EXPEDITE_PRIORITY, "tasks_raised": raised.rowcount},
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(order)
    return order


def list_orders(session: Session, limit: int) -> OrderListOut:
    """Orders, newest first. id breaks ties between orders created in the same millisecond."""
    orders = session.scalars(select(Order).order_by(Order.created_at.desc(), Order.id.desc()).limit(limit)).all()
    items = _orders_out(session, orders)
    return OrderListOut(items=items, count=len(items))


def order_out(session: Session, order: Order) -> OrderOut:
    """The order with its lines, and each line's tasks with their bin locations."""
    return _orders_out(session, [order])[0]


def _orders_out(session: Session, orders: Sequence[Order]) -> list[OrderOut]:
    """Build the response for many orders in two queries, however many orders there are."""
    if not orders:
        return []
    order_ids = [order.id for order in orders]

    lines_by_order: dict[int, list[tuple[OrderLine, str]]] = defaultdict(list)
    for line, code in session.execute(
        select(OrderLine, Sku.code)
        .join(Sku, Sku.id == OrderLine.sku_id)
        .where(OrderLine.order_id.in_(order_ids))
        .order_by(OrderLine.line_no)
    ):
        lines_by_order[line.order_id].append((line, code))

    tasks_by_line: dict[int, list[OrderTaskOut]] = defaultdict(list)
    for task, location in session.execute(
        select(Task, Location)
        .join(Location, Location.id == Task.location_id)
        .where(Task.order_id.in_(order_ids))
        .order_by(Task.id)
    ):
        tasks_by_line[task.order_line_id].append(
            OrderTaskOut(
                task_id=task.id,
                qty=task.qty,
                status=task.status,
                version=task.version,
                location=LocationOut.of(location),
            )
        )
    return [
        OrderOut(
            order_id=order.id,
            external_ref=order.external_ref,
            run_id=order.run_id,
            status=order.status,
            priority=order.priority,
            expedited=order.expedited,
            due_at=order.due_at,
            created_at=order.created_at,
            completed_at=order.completed_at,
            lines=[
                OrderLineOut(
                    order_line_id=line.id, sku_code=code, qty_ordered=line.qty_ordered, tasks=tasks_by_line[line.id]
                )
                for line, code in lines_by_order[order.id]
            ],
        )
        for order in orders
    ]


def _find_by_ref(session: Session, external_ref: str) -> Order | None:
    return session.scalar(select(Order).where(Order.external_ref == external_ref))


def _intake(session: Session, payload: OrderCreate) -> Order:
    if payload.run_id is not None and session.get(SimRun, payload.run_id) is None:
        raise ApiError(422, "unknown_run", f"run_id {payload.run_id} does not exist")

    codes = {line.sku_code for line in payload.lines}
    skus = {sku.code: sku for sku in session.scalars(select(Sku).where(Sku.code.in_(codes)))}
    missing = sorted(codes - skus.keys())
    if missing:
        raise ApiError(422, "unknown_sku", f"Unknown sku_code: {', '.join(missing)}")

    order = Order(
        external_ref=payload.external_ref,
        run_id=payload.run_id,
        priority=payload.priority,
        due_at=payload.due_at,
    )
    session.add(order)
    session.flush()  # assigns order.id
    session.add(
        Event(
            event_type="order_received",
            run_id=order.run_id,
            order_id=order.id,
            payload={"external_ref": order.external_ref, "lines": len(payload.lines)},
        )
    )

    for line_no, line_in in enumerate(payload.lines, start=1):
        sku = skus[line_in.sku_code]
        line = OrderLine(order_id=order.id, line_no=line_no, sku_id=sku.id, qty_ordered=line_in.qty)
        session.add(line)
        session.flush()

        for bin_, qty in _allocate(session, sku, line_in.qty):
            bin_.qty_reserved += qty
            task = Task(
                order_id=order.id,
                order_line_id=line.id,
                sku_id=sku.id,
                location_id=bin_.location_id,
                qty=qty,
                priority=order.priority,
            )
            session.add(task)
            session.flush()
            session.add(
                Event(
                    event_type="task_created",
                    run_id=order.run_id,
                    order_id=order.id,
                    task_id=task.id,
                    payload={"order_line_id": line.id, "location_id": bin_.location_id, "qty": qty},
                )
            )
    return order


def _allocate(session: Session, sku: Sku, qty: int) -> list[tuple[Inventory, int]]:
    """Choose bins for qty units of sku and how many to take from each.

    One bin if any bin can cover the whole line; otherwise split across bins, largest unreserved
    stock first, so the line becomes as few tasks as possible. The SKU's inventory rows stay
    locked (SELECT ... FOR UPDATE) until commit, so concurrent orders can't over-reserve.
    """
    rows = session.scalars(
        select(Inventory).where(Inventory.sku_id == sku.id).order_by(Inventory.location_id).with_for_update()
    ).all()
    bins = sorted(
        (row for row in rows if row.qty_on_hand > row.qty_reserved),
        key=lambda row: (row.qty_reserved - row.qty_on_hand, row.location_id),
    )
    available = sum(row.qty_on_hand - row.qty_reserved for row in bins)
    if available < qty:
        # TODO(team decision): insufficient_stock. Currently rejects the whole order with 409 and
        # writes nothing (design doc default). Alternative: accept the order and open an exception.
        raise InsufficientStock(sku.code, qty, available)

    picks = []
    remaining = qty
    for row in bins:
        take = min(row.qty_on_hand - row.qty_reserved, remaining)
        picks.append((row, take))
        remaining -= take
        if remaining == 0:
            break
    return picks

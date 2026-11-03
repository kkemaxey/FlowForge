"""Offline demo: seed a SQLite file, generate orders, run the simulator in fast-forward, print results.

Everything runs in-process through FastAPI's TestClient against its own SQLite engine, so it needs no
server and no Firebase, and it never touches DATABASE_URL. The token check is replaced on this
in-process app only; the deployed API is unaffected.

place_order() and assign_open_tasks() stand in for Kanayo's intake/task generation and greedy
assigner until those exist. Tests use them too.
"""
from collections import Counter
from pathlib import Path

# TestClient calls the FastAPI app directly in this process, without starting a web server.
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.modules.assignment.models import Assignment
from app.modules.orders.models import Order, OrderLine
from app.modules.simulation.models import Inventory, Location, Sku
from app.modules.simulation.order_generator import OrderGenerator
from app.modules.simulation.seed import SeedConfig, seed_database
from app.modules.simulation.simulator import Simulator, SimulatorConfig
from app.modules.tasks.models import Task
from app.modules.workforce.models import Worker

# How much simulated time passes between ticks. The demo fast-forwards: no real waiting.
SECONDS_PER_TICK = 2.0


def place_order(db: Session, ref: str, lines: list[tuple[str, int]], run_id: int | None = None) -> Order:
    """Stand-in intake: one open task per line, reserved in the bin with the most free stock."""
    order = Order(external_ref=ref, run_id=run_id, status="received")
    db.add(order)
    # flush so order.id exists before the lines and tasks refer to it.
    db.flush()
    for sku_code, qty in lines:
        sku = db.scalar(select(Sku).where(Sku.sku_code == sku_code))
        # Choose the bin with the most free stock that can cover the whole quantity.
        free = Inventory.on_hand - Inventory.reserved
        stock = db.scalar(
            select(Inventory).where(Inventory.sku_id == sku.id, free >= qty).order_by(free.desc(), Inventory.id).limit(1)
        )
        if stock is None:
            raise ValueError(f"no bin can cover {qty} x {sku_code}")
        # Reserve the units so no other task can count on them.
        stock.reserved += qty
        line = OrderLine(order_id=order.id, sku_id=sku.id, qty=qty)
        db.add(line)
        db.flush()
        # One pick task per line, waiting ("open") for the assigner.
        db.add(Task(order_id=order.id, order_line_id=line.id, sku_id=sku.id, location_id=stock.location_id, qty=qty, status="open"))
    db.commit()
    return order


def assign_open_tasks(db: Session) -> int:
    """Stand-in greedy assigner: oldest open task to the lowest-id idle worker. Returns how many were assigned."""
    # Forget cached rows so we see what the API changed.
    db.expire_all()
    assigned = 0
    for task in db.scalars(select(Task).where(Task.status == "open").order_by(Task.id)).all():
        worker = db.scalar(select(Worker).where(Worker.status == "idle").order_by(Worker.id).limit(1))
        # Nobody free: stop; the rest wait for the next round.
        if worker is None:
            break
        # Task -> assigned, worker -> busy, each with a version bump.
        task.status, task.version = "assigned", task.version + 1
        worker.status, worker.version = "busy", worker.version + 1
        # Record who got the task (an append-only history row).
        db.add(Assignment(task_id=task.id, worker_id=worker.id))
        db.flush()
        assigned += 1
    db.commit()
    return assigned


def run_demo(db_path: Path, *, orders: int, seed_config: SeedConfig, sim_config: SimulatorConfig, max_seconds: float) -> None:
    """Set up an isolated app + database for the demo, run it, and always clean up afterwards."""
    from app.main import app

    # A separate database engine for the demo file, so the real DATABASE_URL is never used.
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    # Create any missing tables in the demo file.
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def demo_db():
        # Replacement for get_db: every API request in the demo uses the demo file.
        with sessions() as session:
            yield session

    # Swap the database and the login check, but only on this in-process app object.
    app.dependency_overrides[get_db] = demo_db
    app.dependency_overrides[get_current_user] = lambda: {"uid": "demo", "email": "demo@localhost"}
    try:
        with sessions() as db:
            _run(TestClient(app), db, orders, seed_config, sim_config, max_seconds)
    finally:
        # Undo the overrides even if the demo crashed.
        app.dependency_overrides.clear()
        engine.dispose()
    print(f"\nDatabase kept at {db_path.resolve()}  (inspect with: sqlite3 -header -column {db_path})")


def _run(api: TestClient, db: Session, orders: int, seed_config: SeedConfig, sim_config: SimulatorConfig, max_seconds: float) -> None:
    """The demo itself: seed, place orders, simulate, then print the results."""
    # 1. Fresh warehouse (wipes the demo file first).
    seeded = seed_database(db, seed_config, reset_first=True)
    # Count SKUs stocked in more than one bin, and list the low-stock ones, for the summary.
    multi = db.scalar(select(func.count()).select_from(
        select(Inventory.sku_id).group_by(Inventory.sku_id).having(func.count() > 1).subquery()))
    low = db.execute(
        select(Sku.sku_code, func.sum(Inventory.on_hand)).join(Inventory).group_by(Sku.sku_code)
        .having(func.sum(Inventory.on_hand) <= 3).order_by(Sku.sku_code)
    ).all()
    print(f"== Seeded (seed {seed_config.seed}): {seeded.locations} locations, {seeded.skus} SKUs, "
          f"{seeded.inventory_rows} inventory rows, {seeded.workers} workers/robots")
    print(f"   {multi} SKUs in several bins; low stock: {', '.join(f'{c} ({q})' for c, q in low)}")

    # 2. A fake clock (a list so the lambda sees updates) and a simulator that reads it.
    now = [0.0]
    sim = Simulator(api, sim_config, clock=lambda: now[0])
    run_id = sim.start_run()

    # 3. Orders: the real generator builds them; the stand-in intake stores them.
    generator = OrderGenerator(api, seed=sim_config.seed)
    for _ in range(orders):
        generator.refresh_stock()
        payload = generator.build_order()
        place_order(db, payload["external_ref"], [(line["sku_code"], line["qty"]) for line in payload["lines"]], run_id)
    print(f"== Run {run_id}: {orders} orders, {db.scalar(select(func.count()).select_from(Task))} pick tasks. "
          f"P(stockout/jam/down) = {sim_config.p_stockout}/{sim_config.p_jam}/{sim_config.p_worker_down}")

    # 4. Simulate: assign, tick, advance the clock, until all work is done or time runs out.
    print("== Exceptions and recoveries (simulated time)")
    while now[0] < max_seconds:
        assign_open_tasks(db)
        downed = set(sim.down_until)
        # Print only the interesting actions (exceptions and skipped actions, not normal picks).
        for action in sim.tick():
            if action.outcome != "pick" or not action.ok:
                print(f"   t={now[0]:5.0f}s  task {action.task_id:3d}  {action.outcome:11s} {action.detail}")
        # Workers that were down before this tick and aren't any more just recovered.
        for worker_id in downed - set(sim.down_until):
            print(f"   t={now[0]:5.0f}s  worker {worker_id} recovered")
        now[0] += SECONDS_PER_TICK
        db.expire_all()
        # Stop once nothing is waiting or in progress and nobody is still down.
        working = db.scalar(select(func.count()).where(Task.status.in_(("open", "assigned"))))
        if working == 0 and not sim.down_until:
            break

    # 5. Results: counts by status, then the same endpoints the console would call.
    order_status = Counter(db.scalars(select(Order.status)))
    task_status = Counter(db.scalars(select(Task.status)))
    workers = Counter(db.scalars(select(Worker.status)))
    print(f"== After {now[0]:.0f} simulated seconds")
    print(f"   orders:  {dict(order_status)}")
    print(f"   tasks:   {dict(task_status)}")
    print(f"   workers: {dict(workers)}")

    metric = api.get(f"/api/v1/metrics/throughput?run_id={run_id}&window_minutes=5").json()
    print(f"== GET /api/v1/metrics/throughput?run_id={run_id}&window_minutes=5")
    print(f"   {metric}")
    # location id -> code, so bins print as "A1-04-R" instead of numbers.
    codes = dict(db.execute(select(Location.id, Location.code)).all())
    for label, query in (("open", "true"), ("auto-resolved", "false")):
        listed = api.get(f"/api/v1/exceptions?open={query}").json()
        print(f"== GET /api/v1/exceptions?open={query}  ({len(listed)} {label})")
        for e in listed:
            to = codes.get(e["rerouted_to_location_id"], "-")
            print(f"   #{e['exception_id']:<3} {e['type']:11s} task {e['task_id']:3d}  "
                  f"{codes[e['from_location_id']]} -> {to:8s} task now {e['task_status']}")

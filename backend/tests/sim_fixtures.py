"""Fixtures for simulation/events tests: an in-memory database shared across threads and an authed client.

Import the fixtures you need into a test module: `from tests.sim_fixtures import api, db, db_engine`.
"""
from collections.abc import Generator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app

# Importing these registers every table on Base.metadata.
from app.modules.assignment.models import Assignment
from app.modules.auth import models as _auth  # noqa: F401
from app.modules.events import models as _events  # noqa: F401
from app.modules.orders.models import Order, OrderLine
from app.modules.simulation.models import Inventory, Location, SimRun, Sku
from app.modules.tasks.models import Task
from app.modules.workforce.models import Worker

TEST_USER = {"uid": "test-supervisor", "email": "supervisor@example.test"}


@dataclass
class World:
    run: SimRun
    sku: Sku
    bin_a: Location
    bin_near: Location
    bin_far: Location
    worker: Worker
    order: Order
    task: Task
    assignment: Assignment


def build_world(db: Session, *, near_stock: int = 20, far_stock: int = 50, qty: int = 4) -> World:
    """One SKU in three bins, and a busy worker with an active assignment to pick `qty` from bin A.

    Bin A holds 10 units with this task's qty reserved. The near bin is closer to A than the far one,
    so a reroute should prefer it when it has enough stock.
    """
    run = SimRun(seed=1)
    sku = Sku(sku_code="SKU-0001", name="Test Widget")
    bin_a = Location(code="A1-01-L", zone="A", aisle="A1", x=0, y=2)
    bin_near = Location(code="A1-04-R", zone="A", aisle="A1", x=2, y=5)
    bin_far = Location(code="C2-19-R", zone="C", aisle="C2", x=17, y=20)
    worker = Worker(name="Picker 01", kind="human", speed=1.0, x=1, y=1, status="busy")
    db.add_all([run, sku, bin_a, bin_near, bin_far, worker])
    db.flush()
    db.add_all([
        Inventory(sku_id=sku.id, location_id=bin_a.id, on_hand=10, reserved=qty),
        Inventory(sku_id=sku.id, location_id=bin_near.id, on_hand=near_stock, reserved=0),
        Inventory(sku_id=sku.id, location_id=bin_far.id, on_hand=far_stock, reserved=0),
    ])
    order = Order(external_ref="test-1", run_id=run.id, status="in_progress")
    db.add(order)
    db.flush()
    line = OrderLine(order_id=order.id, sku_id=sku.id, qty=qty)
    db.add(line)
    db.flush()
    task = Task(order_id=order.id, order_line_id=line.id, sku_id=sku.id, location_id=bin_a.id, qty=qty, status="assigned")
    db.add(task)
    db.flush()
    assignment = Assignment(task_id=task.id, worker_id=worker.id)
    db.add(assignment)
    db.commit()
    return World(run, sku, bin_a, bin_near, bin_far, worker, order, task, assignment)


def inventory_at(db: Session, location: Location) -> Inventory:
    db.expire_all()
    return db.query(Inventory).filter_by(location_id=location.id).one()


@pytest.fixture
def db_engine() -> Generator[Engine, None, None]:
    # StaticPool keeps one connection, so the TestClient's worker thread sees the same in-memory DB.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(db_engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Generator[Session, None, None]:
    with session_factory() as session:
        yield session


@pytest.fixture
def api(session_factory: sessionmaker[Session]) -> Generator[TestClient, None, None]:
    """TestClient wired to the test DB, with Firebase auth replaced by a fixed supervisor."""

    def override_get_db() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    yield TestClient(app)
    app.dependency_overrides.clear()



# Stand-ins for Kanayo's intake and assigner, shared with `cli demo`.
from app.modules.simulation.demo import assign_open_tasks, place_order  # noqa: E402, F401

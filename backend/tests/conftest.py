import os
from pathlib import Path

# Database tests run against the MySQL test database (TEST_DATABASE_URL, set in backend/.env and
# loaded into the Docker backend container), never the dev database:
#     docker compose exec backend pytest
# Without TEST_DATABASE_URL (e.g. CI with no MySQL service yet) the app gets a throwaway SQLite
# database and tests that use the `db` fixture are skipped. Set before the app is imported.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
os.environ["DATABASE_URL"] = TEST_DATABASE_URL or "sqlite://"
# Tests run assigner passes themselves; the background loop would race them.
os.environ["ASSIGNER_LOOP_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.main import app

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(scope="session")
def migrated_db() -> None:
    """Bring the test database schema to the latest migration, once per test run."""
    if not TEST_DATABASE_URL:
        pytest.skip("needs MySQL: run inside Docker with `docker compose exec backend pytest`")
    from alembic import command
    from alembic.config import Config

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(config, "head")


@pytest.fixture
def db(migrated_db) -> Session:
    """A session on an emptied test database.

    DELETE is much faster than TRUNCATE on small InnoDB tables. The append-only events table
    blocks DELETE with a trigger, so it is TRUNCATEd instead (TRUNCATE doesn't fire triggers).
    The session sees a snapshot; call db.rollback() before reading rows that an API request wrote.
    """
    with engine.begin() as conn:
        tables = [row[0] for row in conn.execute(text("SHOW TABLES")) if row[0] != "alembic_version"]
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in tables:
            verb = "TRUNCATE TABLE" if table == "events" else "DELETE FROM"
            conn.execute(text(f"{verb} `{table}`"))
        conn.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
    with SessionLocal() as session:
        yield session


@pytest.fixture
def floor(db):
    """Factories for a tiny warehouse, committed straight to the test database.

    floor.order(...)              a new order (with one line); floor.order_id is the default one
    floor.task(x, y, ...)         a task in its own bin at (x, y), on the default order unless given
    floor.worker(x, y, ...)       a worker
    floor.assign(task, worker)    an open assignment (task and worker statuses are left as given)
    """
    from datetime import datetime, timedelta

    from app.modules.assignment.models import Assignment, AssignmentSource
    from app.modules.orders.models import Order, OrderLine, OrderStatus
    from app.modules.simulation.models import SimRun
    from app.modules.tasks.models import Task, TaskStatus
    from app.modules.warehouse.models import Location, LocationKind, Sku
    from app.modules.workforce.models import Worker, WorkerKind, WorkerStatus

    t0 = datetime(2026, 11, 3, 12, 0, 0)
    run = SimRun(algorithm="greedy_v1", seed=1, order_rate=1.0)
    sku = Sku(code="SKU-T", name="Test shoe")
    db.add_all([run, sku])
    db.commit()
    lines: dict[int, int] = {}  # order id -> its line id

    class Floor:
        run_id = run.id
        order_id: int

        @staticmethod
        def order(status=OrderStatus.open, priority=0):
            order = Order(external_ref=f"ORD-{len(lines) + 1}", run_id=run.id, status=status, priority=priority)
            db.add(order)
            db.flush()
            line = OrderLine(order_id=order.id, line_no=1, sku_id=sku.id, qty_ordered=1)
            db.add(line)
            db.commit()
            lines[order.id] = line.id
            return order

        @staticmethod
        def task(x, y, priority=0, minutes=0, status=TaskStatus.open, order=None):
            order_id = order.id if order is not None else Floor.order_id
            location = Location(x=x, y=y, kind=LocationKind.storage)
            db.add(location)
            db.flush()
            task = Task(
                order_id=order_id, order_line_id=lines[order_id], sku_id=sku.id, location_id=location.id, qty=1,
                status=status, priority=priority, created_at=t0 + timedelta(minutes=minutes),
            )
            db.add(task)
            db.commit()
            return task

        @staticmethod
        def worker(x, y, status=WorkerStatus.idle, is_active=True):
            worker = Worker(name=f"W{x}{y}", kind=WorkerKind.human, x=x, y=y, status=status, is_active=is_active)
            db.add(worker)
            db.commit()
            return worker

        @staticmethod
        def assign(task, worker, source=AssignmentSource.scheduler):
            assignment = Assignment(task_id=task.id, worker_id=worker.id, source=source)
            db.add(assignment)
            db.commit()
            return assignment

    Floor.order_id = Floor.order().id
    return Floor

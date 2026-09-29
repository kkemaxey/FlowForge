from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, build_engine
from app.modules.metrics.repository import SqlEventRepository
from app.modules.workforce.repository import SqlWorkerRepository

NOW = datetime(2026, 9, 29, 12, 0, 0)


@pytest.fixture
def session():
    engine = build_engine("sqlite://")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as db_session:
        yield db_session
    engine.dispose()


def add_worker(repo, name="Ana", worker_type="human", status="idle"):
    return repo.add(name=name, worker_type=worker_type, speed=1.5, cur_x=2, cur_y=3,
                    status=status, enabled=True)


def test_worker_round_trip(session):
    repo = SqlWorkerRepository(session)

    created = add_worker(repo)
    fetched = repo.get(created.id)
    updated = repo.update(created.id, {"name": "Ana B", "cur_x": 5})
    repo.delete(created.id)

    assert fetched == created
    assert (updated.name, updated.cur_x, updated.cur_y) == ("Ana B", 5, 3)
    assert repo.get(created.id) is None


def test_worker_list_filters(session):
    repo = SqlWorkerRepository(session)
    add_worker(repo, name="A", worker_type="human", status="idle")
    add_worker(repo, name="B", worker_type="robot", status="idle")
    add_worker(repo, name="C", worker_type="robot", status="busy")

    assert [w.name for w in repo.list_workers()] == ["A", "B", "C"]
    assert [w.name for w in repo.list_workers(worker_type="robot")] == ["B", "C"]
    assert [w.name for w in repo.list_workers(status="busy")] == ["C"]


def test_get_missing_worker_returns_none(session):
    assert SqlWorkerRepository(session).get(404) is None


def test_event_queries_are_filtered_and_ordered(session):
    repo = SqlEventRepository(session)
    old = repo.add("task_picked", NOW - timedelta(hours=2), 1, 7, 4, None)
    assigned = repo.add("task_assigned", NOW - timedelta(minutes=10), 2, 7, None, None)
    completed = repo.add("order_completed", NOW - timedelta(minutes=5), None, None, None, {"order_id": 9})
    picked = repo.add("task_picked", NOW - timedelta(minutes=1), 2, 7, 3, None)

    assert repo.list_since(NOW - timedelta(minutes=30)) == [assigned, completed, picked]
    assert repo.list_task_events() == [old, assigned, picked]
    assert completed.payload == {"order_id": 9}

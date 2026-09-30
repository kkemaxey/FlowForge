from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.services import create_worker, list_workers


def make_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return Session(engine)


def test_list_workers_seeds_defaults_and_serializes_core_fields():
    with make_session() as session:
        workers = list_workers(session)

    assert [worker["name"] for worker in workers] == ["Worker 1", "Robot 1"]
    assert workers[0]["type"] == "human"
    assert workers[0]["enabled"] is True


def test_create_worker_persists_and_returns_worker_payload():
    with make_session() as session:
        worker = create_worker(
            session,
            {
                "name": "Quality Bot",
                "worker_type": "robot",
                "speed": 3,
                "cur_x": 2,
                "cur_y": 6,
                "status": "idle",
                "enabled": True,
            },
        )

        stored_workers = list_workers(session)

    assert worker["id"] == 1
    assert worker["type"] == "robot"
    assert stored_workers[0]["name"] == "Quality Bot"
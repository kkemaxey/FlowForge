import pytest
from sqlalchemy import select

from app.core.database import utcnow
from app.modules.events.models import Event
from app.modules.events.service import record_event
from app.modules.simulation.models import SimRun
from tests.sim_fixtures import db, db_engine, session_factory  # noqa: F401


def test_record_event_stamps_active_run(db):
    db.add_all([SimRun(seed=1, ended_at=utcnow()), SimRun(seed=2)])
    db.flush()
    active = db.scalar(select(SimRun).where(SimRun.seed == 2))

    record_event(db, "task_picked", task_id=7, payload={"qty": 3})
    db.commit()

    event = db.scalar(select(Event))
    assert event.run_id == active.id
    assert event.task_id == 7
    assert event.payload == {"qty": 3}


def test_record_event_without_active_run_has_no_run_id(db):
    record_event(db, "order_received", order_id=1)
    db.commit()

    assert db.scalar(select(Event.run_id)) is None


def test_record_event_rejects_unknown_type(db):
    with pytest.raises(ValueError):
        record_event(db, "task_teleported")

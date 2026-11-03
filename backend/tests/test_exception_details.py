"""The columns migration 0004 adds to exceptions, against the MySQL test database."""
import pytest
from sqlalchemy.exc import IntegrityError

from app.modules.simulation.models import ExceptionType, TaskException
from app.modules.warehouse.models import Location, LocationKind


def test_exception_stores_its_details(db, floor):
    task = floor.task(1, 1)
    destination = Location(x=2, y=2, kind=LocationKind.storage)
    db.add(destination)
    db.commit()

    exception = TaskException(
        task_id=task.id,
        run_id=floor.run_id,
        type=ExceptionType.stockout,
        qty_found=1,
        from_location_id=task.location_id,
        rerouted_to_location_id=destination.id,
    )
    db.add(exception)
    db.commit()
    db.expire_all()

    stored = db.get(TaskException, exception.id)
    assert stored.run_id == floor.run_id
    assert stored.qty_found == 1
    assert stored.from_location_id == task.location_id
    assert stored.rerouted_to_location_id == destination.id


def test_exception_needs_a_from_location(db, floor):
    task = floor.task(1, 1)
    db.add(TaskException(task_id=task.id, type=ExceptionType.jam))

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_exception_rejects_an_unknown_location(db, floor):
    task = floor.task(1, 1)
    db.add(TaskException(task_id=task.id, type=ExceptionType.jam, from_location_id=999_999))

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

import pytest

from app.services.errors import ConflictError, NotFoundError, RuleViolationError
from app.services.workforce import GridBounds, WorkforceService
from tests.unit.fakes import FakeWorkerRepository, make_worker

GRID = GridBounds(width=20, height=12)


def service_with(*workers):
    repo = FakeWorkerRepository(workers)
    return WorkforceService(repo, GRID), repo


def test_create_worker_starts_idle_and_gets_an_id():
    service, repo = service_with()

    worker = service.create_worker(name="Ana", worker_type="human", speed=1.5, cur_x=3, cur_y=4)

    assert worker.id == 1
    assert worker.status == "idle"
    assert worker.enabled is True
    assert repo.get(1) == worker


def test_create_worker_accepts_the_far_grid_corner():
    service, _ = service_with()

    worker = service.create_worker(name="Edge", worker_type="robot", speed=2.0, cur_x=19, cur_y=11)

    assert (worker.cur_x, worker.cur_y) == (19, 11)


@pytest.mark.parametrize("cur_x, cur_y", [(20, 0), (0, 12), (-1, 0), (0, -1)])
def test_create_worker_rejects_positions_off_the_grid(cur_x, cur_y):
    service, repo = service_with()

    with pytest.raises(RuleViolationError) as error:
        service.create_worker(name="Lost", worker_type="human", speed=1.0, cur_x=cur_x, cur_y=cur_y)

    assert error.value.code == "position_off_grid"
    assert repo.list_workers() == []


def test_list_workers_filters_by_status_and_type():
    service, _ = service_with(
        make_worker(id=1, type="human", status="idle"),
        make_worker(id=2, type="robot", status="idle"),
        make_worker(id=3, type="robot", status="busy"),
    )

    assert [w.id for w in service.list_workers()] == [1, 2, 3]
    assert [w.id for w in service.list_workers(worker_type="robot")] == [2, 3]
    assert [w.id for w in service.list_workers(status="idle", worker_type="robot")] == [2]


def test_get_worker_raises_not_found():
    service, _ = service_with()

    with pytest.raises(NotFoundError) as error:
        service.get_worker(99)

    assert error.value.code == "worker_not_found"


def test_update_worker_applies_changes():
    service, _ = service_with(make_worker(id=1, name="Old"))

    updated = service.update_worker(1, {"name": "New", "speed": 3.0})

    assert updated.name == "New"
    assert updated.speed == 3.0


def test_update_worker_rejects_status_changes():
    service, repo = service_with(make_worker(id=1))

    with pytest.raises(RuleViolationError) as error:
        service.update_worker(1, {"status": "busy"})

    assert error.value.code == "field_not_editable"
    assert repo.get(1).status == "idle"


def test_update_worker_checks_new_position_against_existing_coordinate():
    service, _ = service_with(make_worker(id=1, cur_x=0, cur_y=11))

    with pytest.raises(RuleViolationError) as error:
        service.update_worker(1, {"cur_x": 20})

    assert error.value.code == "position_off_grid"


def test_update_worker_with_no_changes_returns_current_worker():
    original = make_worker(id=1)
    service, _ = service_with(original)

    assert service.update_worker(1, {}) == original


def test_update_missing_worker_raises_not_found():
    service, _ = service_with()

    with pytest.raises(NotFoundError):
        service.update_worker(5, {"name": "Ghost"})


def test_delete_idle_worker_removes_it():
    service, repo = service_with(make_worker(id=1, status="idle"))

    service.delete_worker(1)

    assert repo.get(1) is None


def test_delete_busy_worker_is_a_conflict():
    service, repo = service_with(make_worker(id=1, status="busy"))

    with pytest.raises(ConflictError) as error:
        service.delete_worker(1)

    assert error.value.code == "worker_busy"
    assert repo.get(1) is not None


def test_delete_missing_worker_raises_not_found():
    service, _ = service_with()

    with pytest.raises(NotFoundError):
        service.delete_worker(1)

import pytest

from app.core.errors import ConflictError, ValidationFailedError
from app.modules.workforce.schema import WorkerCreate, WorkerStatus, WorkerType
from app.modules.workforce.service import WorkerService
from tests.unit.fakes import FakeWorkerRepository


@pytest.fixture
def service():
    return WorkerService(FakeWorkerRepository())


def worker_request(**overrides) -> WorkerCreate:
    fields = {"name": "Maria Lopez", "type": "human", "speed": 1.2}
    fields.update(overrides)
    return WorkerCreate(**fields)


def test_new_worker_starts_idle_and_enabled_at_the_dock(service):
    worker = service.create_worker(worker_request())
    assert worker.id == 1
    assert worker.status == WorkerStatus.IDLE
    assert worker.enabled is True
    assert (worker.cur_x, worker.cur_y) == (0, 0)


def test_worker_keeps_the_position_it_was_given(service):
    worker = service.create_worker(worker_request(cur_x=19, cur_y=11))
    assert (worker.cur_x, worker.cur_y) == (19, 11)


def test_duplicate_name_is_rejected_ignoring_case(service):
    service.create_worker(worker_request(name="Maria Lopez"))
    with pytest.raises(ConflictError):
        service.create_worker(worker_request(name="maria lopez"))


def test_human_cannot_move_faster_than_the_human_limit(service):
    with pytest.raises(ValidationFailedError, match="human"):
        service.create_worker(worker_request(speed=2.5))


def test_robot_may_move_faster_than_a_human(service):
    worker = service.create_worker(worker_request(name="PickBot-7", type="robot", speed=3.5))
    assert worker.type == WorkerType.ROBOT
    with pytest.raises(ValidationFailedError, match="robot"):
        service.create_worker(worker_request(name="PickBot-8", type="robot", speed=4.5))


def test_disabled_worker_cannot_be_busy(service):
    with pytest.raises(ValidationFailedError):
        service.create_worker(worker_request(status="busy", enabled=False))


def test_rejected_worker_is_not_saved(service):
    with pytest.raises(ValidationFailedError):
        service.create_worker(worker_request(speed=9))
    assert service.list_workers() == []


def test_list_returns_workers_in_the_order_they_were_added(service):
    for name in ("Ana", "Ben", "Cy"):
        service.create_worker(worker_request(name=name))
    assert [worker.name for worker in service.list_workers()] == ["Ana", "Ben", "Cy"]


def test_list_filters_by_type_and_status(service):
    service.create_worker(worker_request(name="Ana"))
    service.create_worker(worker_request(name="PickBot-1", type="robot", speed=3))
    service.create_worker(worker_request(name="PickBot-2", type="robot", speed=3, status="busy"))

    robots = service.list_workers(worker_type=WorkerType.ROBOT)
    assert [worker.name for worker in robots] == ["PickBot-1", "PickBot-2"]
    idle_robots = service.list_workers(WorkerType.ROBOT, WorkerStatus.IDLE)
    assert [worker.name for worker in idle_robots] == ["PickBot-1"]

"""Workforce service functions other modules call, against the MySQL test database."""
from app.modules.workforce.models import WorkerStatus
from app.modules.workforce.service import list_idle_workers


def test_list_idle_workers_skips_inactive_and_busy(db, floor):
    first = floor.worker(1, 1)
    floor.worker(2, 2, is_active=False)  # idle but deactivated
    floor.worker(3, 3, status=WorkerStatus.busy)
    floor.worker(4, 4, status=WorkerStatus.down)
    second = floor.worker(5, 5)

    workers = list_idle_workers(db)

    assert [w.id for w in workers] == [first.id, second.id]

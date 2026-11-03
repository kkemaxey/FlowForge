"""Workforce service: the grid bounds check (pure) and list_idle_workers (MySQL test database)."""
import pytest

from app.modules.workforce.models import WorkerStatus
from app.modules.workforce.service import list_idle_workers, position_in_bounds

BOUNDS = (9, 9)  # a 10 x 10 grid: x and y run 0..9


@pytest.mark.parametrize(
    ("x", "y", "expected"),
    [
        (0, 0, True),  # corner
        (9, 9, True),  # far corner, inclusive
        (9, 0, True),
        (0, 9, True),
        (10, 0, False),  # max + 1
        (0, 10, False),
        (10, 10, False),
        (-1, 0, False),  # negative
        (0, -1, False),
    ],
)
def test_position_in_bounds_edges(x, y, expected):
    assert position_in_bounds(x, y, BOUNDS) is expected


def test_position_in_bounds_non_square_grid():
    assert position_in_bounds(19, 11, (19, 11)) is True
    assert position_in_bounds(12, 11, (19, 11)) is True
    assert position_in_bounds(11, 12, (19, 11)) is False


def test_position_in_bounds_without_grid_allows_anything():
    # No locations yet: there is no grid to check against.
    assert position_in_bounds(0, 0, None) is True
    assert position_in_bounds(500, 500, None) is True


def test_list_idle_workers_skips_inactive_and_busy(db, floor):
    first = floor.worker(1, 1)
    floor.worker(2, 2, is_active=False)  # idle but deactivated
    floor.worker(3, 3, status=WorkerStatus.busy)
    floor.worker(4, 4, status=WorkerStatus.down)
    second = floor.worker(5, 5)

    workers = list_idle_workers(db)

    assert [w.id for w in workers] == [first.id, second.id]

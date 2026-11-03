import pytest
from sqlalchemy import func, select

from app.modules.simulation.models import Inventory, Location, SimRun, Sku
from app.modules.simulation.seed import SeedConfig, SeedError, seed_database
from app.modules.workforce.models import Worker
from tests.sim_fixtures import db, db_engine, session_factory  # noqa: F401


def snapshot(db) -> dict:
    """Everything the seed generates, minus ids and timestamps."""
    inventory = db.execute(
        select(Sku.sku_code, Location.code, Inventory.on_hand)
        .join(Sku, Inventory.sku_id == Sku.id)
        .join(Location, Inventory.location_id == Location.id)
        .order_by(Sku.sku_code, Location.code)
    ).all()
    workers = db.execute(select(Worker.name, Worker.kind, Worker.speed, Worker.x, Worker.y).order_by(Worker.name)).all()
    skus = db.execute(select(Sku.sku_code, Sku.name).order_by(Sku.sku_code)).all()
    return {"inventory": inventory, "workers": workers, "skus": skus}


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_seed_builds_expected_world(db):
    result = seed_database(db, SeedConfig(seed=1))

    assert result.skus == 25 and count(db, Sku) == 25
    assert count(db, Worker) == 10  # 5 pickers + 5 robots
    assert db.scalar(select(func.count()).where(Worker.status != "idle")) == 0
    assert count(db, Location) == result.locations
    assert db.scalar(select(func.count()).where(Location.kind == "station")) == 3
    assert db.scalar(select(SimRun.id)) == result.run_id
    assert db.scalar(select(func.sum(Inventory.reserved))) == 0
    # One 10x10 warehouse: everything on the grid, at most one location per cell.
    assert result.locations == 45
    assert db.scalar(select(func.max(Location.x))) < 10
    assert db.scalar(select(func.max(Location.y))) < 10
    cells = db.execute(select(Location.x, Location.y)).all()
    assert len(set(cells)) == len(cells) <= 100


def test_seed_spreads_some_skus_and_starves_others(db):
    seed_database(db, SeedConfig(seed=1))

    per_sku = db.execute(
        select(Inventory.sku_id, func.count(), func.sum(Inventory.on_hand)).group_by(Inventory.sku_id)
    ).all()
    assert any(bins >= 2 for _, bins, _ in per_sku), "some SKUs should sit in several bins"
    assert sum(1 for _, _, total in per_sku if total <= 3) == 3, "three SKUs should be low stock"


def test_same_seed_gives_same_data(session_factory):
    snapshots = []
    for _ in range(2):
        with session_factory() as db:
            seed_database(db, SeedConfig(seed=42), reset_first=True)
            snapshots.append(snapshot(db))
    assert snapshots[0] == snapshots[1]


def test_different_seed_gives_different_data(db):
    seed_database(db, SeedConfig(seed=1))
    first = snapshot(db)
    seed_database(db, SeedConfig(seed=2), reset_first=True)
    assert snapshot(db) != first


def test_rerun_without_reset_changes_nothing(db):
    seed_database(db, SeedConfig(seed=1))
    before = snapshot(db)

    assert seed_database(db, SeedConfig(seed=99)) is None
    assert snapshot(db) == before
    assert count(db, SimRun) == 1


def test_sizes_are_configurable(db):
    result = seed_database(db, SeedConfig(seed=1, width=13, height=12, skus=20, workers=2, robots=1, low_stock_skus=2))

    assert result.skus == 20
    assert result.workers == 3
    assert db.scalar(select(func.max(Location.x))) < 13


def test_grid_too_small_for_skus_fails_cleanly(db):
    with pytest.raises(SeedError):
        seed_database(db, SeedConfig(seed=1, width=4, height=5, skus=50))


def test_reset_refused_on_non_sqlite(db, monkeypatch):
    monkeypatch.setattr("app.modules.simulation.seed.reset_allowed", lambda db: False)
    with pytest.raises(SeedError):
        seed_database(db, SeedConfig(seed=1), reset_first=True)

import pytest
from sqlalchemy import func, select

from app.modules.assignment.models import Assignment
from app.modules.events.models import Event
from app.modules.orders.models import Order
from app.modules.simulation.models import Inventory, Sku
from app.modules.simulation.seed import SeedConfig, seed_database
from app.modules.simulation.simulator import Simulator, SimulatorConfig, trigger_exception
from app.modules.tasks.models import Task
from app.modules.workforce.models import Worker
from tests.sim_fixtures import (  # noqa: F401
    api,
    assign_open_tasks,
    db,
    db_engine,
    place_order,
    session_factory,
)

QUIET = {"p_stockout": 0.0, "p_jam": 0.0, "p_worker_down": 0.0}


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def warehouse(db):
    seed_database(db, SeedConfig(seed=11, width=13, height=12, skus=20, workers=2, robots=1, low_stock_skus=2))


def skus_with(db, *, min_bins=1, min_free=1, max_total=None) -> list[str]:
    free = func.sum(Inventory.on_hand - Inventory.reserved)
    query = (
        select(Sku.sku_code).join(Inventory, Inventory.sku_id == Sku.id).group_by(Sku.sku_code)
        .having(func.count() >= min_bins, func.min(Inventory.on_hand - Inventory.reserved) >= min_free)
        .order_by(Sku.sku_code)
    )
    if max_total is not None:
        query = query.having(free <= max_total)
    return list(db.scalars(query))


def drive(sim, db, clock, until, steps=200, seconds_per_step=3.0):
    """Assign, tick, advance time, until `until()` holds."""
    for _ in range(steps):
        assign_open_tasks(db)
        sim.tick()
        clock.now += seconds_per_step
        db.expire_all()
        if until():
            return
    pytest.fail("simulation did not reach the expected state")


def order_status(db, order_id):
    db.expire_all()
    return db.get(Order, order_id).status


def test_simulator_completes_an_order_end_to_end(api, db, warehouse):
    clock = FakeClock()
    sim = Simulator(api, SimulatorConfig(seed=7, pick_seconds=2, **QUIET), clock=clock)
    run_id = sim.start_run()
    codes = skus_with(db, min_free=10)[:3]
    before = {c: db.scalar(select(func.sum(Inventory.on_hand)).join(Sku).where(Sku.sku_code == c)) for c in codes}
    order = place_order(db, "e2e-1", [(codes[0], 2), (codes[1], 1), (codes[2], 3)], run_id=run_id)

    assign_open_tasks(db)
    assert sim.tick() == [], "nobody can pick on the tick they were assigned: they still have to walk"

    drive(sim, db, clock, until=lambda: order_status(db, order.id) == "complete")

    tasks = db.scalars(select(Task).where(Task.order_id == order.id)).all()
    assert {t.status for t in tasks} == {"complete"}
    assert {a.outcome for a in db.scalars(select(Assignment))} == {"completed"}
    assert {w.status for w in db.scalars(select(Worker))} == {"idle"}
    assert db.scalar(select(func.sum(Inventory.reserved))) == 0
    for code, qty in zip(codes, (2, 1, 3)):
        assert db.scalar(select(func.sum(Inventory.on_hand)).join(Sku).where(Sku.sku_code == code)) == before[code] - qty

    types = [e.type for e in db.scalars(select(Event).where(Event.run_id == run_id))]
    assert types.count("task_picked") == 3 and types.count("order_completed") == 1

    metric = api.get(f"/api/v1/metrics/throughput?run_id={run_id}&window_minutes=60").json()
    assert metric["picks"] == 3


def test_travel_time_follows_manhattan_distance_and_speed():
    sim = Simulator(client=None, config=SimulatorConfig(worker_speed=2.0, pick_seconds=5, **QUIET), clock=lambda: 100.0)
    assignment = {"worker_x": 0, "worker_y": 0, "location_x": 3, "location_y": 4, "worker_speed": 1.5}

    plan = sim._plan(assignment, now=100.0)

    assert plan.due_at == pytest.approx(100 + 7 / 3.0 + 5)
    assert plan.outcome == "pick"


def test_forced_jam_reroutes_and_the_order_still_completes(api, db, warehouse):
    clock = FakeClock()
    sim = Simulator(api, SimulatorConfig(seed=7, pick_seconds=1, **QUIET), clock=clock)
    run_id = sim.start_run()
    code = skus_with(db, min_bins=2, min_free=2)[0]
    order = place_order(db, "e2e-jam", [(code, 2)], run_id=run_id)
    task = db.scalar(select(Task).where(Task.order_id == order.id))
    first_bin = task.location_id
    sim.force(task.id, "jam")

    drive(sim, db, clock, until=lambda: order_status(db, order.id) == "complete")

    outcomes = [a.outcome for a in db.scalars(select(Assignment).where(Assignment.task_id == task.id).order_by(Assignment.id))]
    assert outcomes == ["failed", "completed"]
    assert db.get(Task, task.id).location_id != first_bin
    assert api.get("/api/v1/exceptions?open=true").json() == [], "the reroute handled it"
    listed = api.get("/api/v1/exceptions?open=false").json()
    assert [(e["type"], e["task_id"], e["from_location_id"]) for e in listed] == [("jam", task.id, first_bin)]


def test_short_bin_becomes_a_natural_stockout_and_waits_for_supervisor(api, db, warehouse):
    clock = FakeClock()
    sim = Simulator(api, SimulatorConfig(seed=7, pick_seconds=1, **QUIET), clock=clock)
    sim.start_run()
    code = skus_with(db, max_total=3)[0]
    stock = db.scalar(select(Inventory).join(Sku).where(Sku.sku_code == code))
    qty = stock.on_hand
    order = place_order(db, "e2e-short", [(code, qty)])
    # Phantom inventory: the system believed `qty` units were there, one is missing.
    stock.on_hand = qty - 1
    db.commit()
    task_id = db.scalar(select(Task.id).where(Task.order_id == order.id))

    drive(sim, db, clock, until=lambda: db.get(Task, task_id).status == "exception")

    listed = api.get("/api/v1/exceptions?open=true").json()
    assert [(e["type"], e["qty_found"], e["rerouted_to_location_id"]) for e in listed] == [("stockout", qty - 1, None)]
    assert order_status(db, order.id) != "complete"


def test_same_seed_gives_same_outcomes():
    assignment = {"worker_x": 0, "worker_y": 0, "location_x": 1, "location_y": 1, "worker_speed": 1.0}
    config = dict(seed=5, p_stockout=0.2, p_jam=0.2, p_worker_down=0.2)

    a, b = (Simulator(None, SimulatorConfig(**config)) for _ in range(2))
    seq_a = [a._plan(assignment, 0.0).outcome for _ in range(50)]
    seq_b = [b._plan(assignment, 0.0).outcome for _ in range(50)]

    assert seq_a == seq_b
    assert {"pick", "stockout", "jam", "worker_down"} <= set(seq_a)


@pytest.mark.parametrize(
    "bad",
    [{"tick_seconds": 0}, {"worker_speed": -1}, {"p_jam": -0.1}, {"p_stockout": 0.6, "p_jam": 0.6}],
)
def test_bad_config_is_rejected(bad):
    with pytest.raises(ValueError):
        SimulatorConfig(**bad)


def test_manual_trigger_raises_on_the_active_assignment(api, db, warehouse):
    code = skus_with(db, min_bins=2, min_free=2)[0]
    order = place_order(db, "trigger-1", [(code, 1)])
    assign_open_tasks(db)
    task_id = db.scalar(select(Task.id).where(Task.order_id == order.id))

    result = trigger_exception(api, task_id, "stockout")

    assert result["type"] == "stockout"
    assert result["task_status"] == "open"
    with pytest.raises(ValueError):
        trigger_exception(api, task_id, "jam")  # no active assignment any more


def test_downed_worker_recovers_after_the_configured_delay(api, db, warehouse):
    clock = FakeClock()
    sim = Simulator(api, SimulatorConfig(seed=7, pick_seconds=1, recovery_seconds=20, **QUIET), clock=clock)
    sim.start_run()
    code = skus_with(db, min_free=2)[0]
    order = place_order(db, "down-1", [(code, 1)])
    assign_open_tasks(db)
    task = db.scalar(select(Task).where(Task.order_id == order.id))
    worker_id = db.scalar(select(Assignment.worker_id).where(Assignment.task_id == task.id))
    sim.force(task.id, "worker_down")

    def worker_status():
        db.expire_all()
        return db.get(Worker, worker_id).status

    drive(sim, db, clock, until=lambda: worker_status() == "down", seconds_per_step=1)
    went_down_at = clock.now
    drive(sim, db, clock, until=lambda: worker_status() == "idle", seconds_per_step=1)

    assert 20 <= clock.now - went_down_at <= 22
    assert api.get("/api/v1/exceptions?open=true").json() == [], "worker_down reopens the task, so it is handled"
    drive(sim, db, clock, until=lambda: order_status(db, order.id) == "complete")


def test_recover_endpoint_rejects_workers_that_are_not_down(api, db, warehouse):
    worker_id = db.scalar(select(Worker.id).limit(1))

    response = api.post(f"/api/v1/simulation/workers/{worker_id}/recover")

    assert response.status_code == 409
    assert response.json()["code"] == "state_conflict"
    assert api.post("/api/v1/simulation/workers/9999/recover").status_code == 404

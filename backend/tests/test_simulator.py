"""The worker simulator, driving the real API against the MySQL test database with a fake clock."""
import httpx
import pytest
from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.modules.assignment import service as assigner
from app.modules.assignment.models import Assignment, AssignmentOutcome
from app.modules.events.models import Event
from app.modules.orders.models import Order, OrderStatus
from app.modules.simulation import cli
from app.modules.simulation.client import ApiCallError, client_from_env
from app.modules.simulation.simulator import Simulator, SimulatorConfig, trigger_exception
from app.modules.tasks.models import Task, TaskStatus
from app.modules.warehouse.models import Inventory, Location, LocationKind, Sku
from app.modules.workforce.models import Worker, WorkerStatus

QUIET = {"p_stockout": 0.0, "p_jam": 0.0, "p_worker_down": 0.0}
ACTIVE_URL = "/api/v1/simulation/assignments/active"


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def fresh(model, id_):
    with SessionLocal() as session:
        return session.get(model, id_)


@pytest.fixture
def stock(db, floor):
    """Put the floor's shoe (SKU-T) in bins: stock({(x, y): on_hand, ...}) returns their ids."""
    sku_id = db.scalar(select(Sku.id).where(Sku.code == "SKU-T"))

    def make(bins):
        ids = {}
        for (x, y), qty in bins.items():
            location = Location(x=x, y=y, kind=LocationKind.storage)
            db.add(location)
            db.flush()
            db.add(Inventory(location_id=location.id, sku_id=sku_id, qty_on_hand=qty))
            ids[(x, y)] = location.id
        db.commit()
        return ids

    return make


def place_order(client, floor, ref, qty=1):
    body = {"external_ref": ref, "run_id": floor.run_id, "lines": [{"sku_code": "SKU-T", "qty": qty}]}
    response = client.post("/api/v1/orders", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def order_tasks(order):
    return [task for line in order["lines"] for task in line["tasks"]]


def assign():
    with SessionLocal() as session:
        return assigner.run_pass(session).assignments


def drive(sim, clock, until, steps=200, seconds_per_step=3.0):
    """Assign, tick and advance time until `until()` holds."""
    for _ in range(steps):
        assign()
        sim.tick()
        clock.now += seconds_per_step
        if until():
            return
    pytest.fail("simulation did not reach the expected state")


def order_status(order_id):
    return fresh(Order, order_id).status


def test_completes_an_order_end_to_end(client, floor, stock):
    bins = stock({(4, 4): 10})
    floor.worker(0, 0)
    clock = FakeClock()
    sim = Simulator(client, SimulatorConfig(seed=7, pick_seconds=2, **QUIET), clock=clock)
    order = place_order(client, floor, "E2E-1", qty=3)

    assign()
    assert sim.tick() == [], "a worker can't pick on the tick they were assigned: they have to walk there"

    clock.now += 100
    actions = sim.tick()

    assert [(a.outcome, a.ok) for a in actions] == [("pick", True)]
    assert order_status(order["order_id"]) is OrderStatus.complete
    with SessionLocal() as session:
        stored = session.get(Inventory, (bins[(4, 4)], session.scalar(select(Sku.id).where(Sku.code == "SKU-T"))))
        assert (stored.qty_on_hand, stored.qty_reserved) == (7, 0)
        assert session.scalar(select(Assignment.outcome)) is AssignmentOutcome.completed
    assert client.get("/api/v1/events/metrics").json()["units_per_hour"] == 36


def test_waits_until_the_walk_and_pick_are_done(client, floor, stock):
    stock({(4, 4): 10})
    floor.worker(0, 0)  # 8 cells away at speed 1, so due at 8 + 2 = 10 seconds
    clock = FakeClock()
    sim = Simulator(client, SimulatorConfig(seed=7, pick_seconds=2, **QUIET), clock=clock)
    place_order(client, floor, "TIME-1")
    assign()

    assert sim.tick() == []
    clock.now = 9.9
    assert sim.tick() == []
    clock.now = 10.0
    assert [a.outcome for a in sim.tick()] == ["pick"]


def test_travel_time_follows_manhattan_distance_and_speed():
    sim = Simulator(client=None, config=SimulatorConfig(worker_speed=2.0, pick_seconds=5, **QUIET))
    assignment = {"worker_x": 0, "worker_y": 0, "location_x": 3, "location_y": 4, "worker_speed": 1.5}

    plan = sim._plan(assignment, now=100.0)

    assert plan.due_at == pytest.approx(100 + 7 / 3.0 + 5)
    assert plan.outcome == "pick"


def test_forced_jam_reroutes_and_the_order_still_completes(client, floor, stock):
    bins = stock({(1, 1): 5, (2, 2): 5})
    floor.worker(0, 0)
    clock = FakeClock()
    sim = Simulator(client, SimulatorConfig(seed=7, pick_seconds=1, **QUIET), clock=clock)
    order = place_order(client, floor, "JAM-1")
    task_id = order_tasks(order)[0]["task_id"]
    first_bin = order_tasks(order)[0]["location"]["location_id"]
    sim.force(task_id, "jam")

    drive(sim, clock, until=lambda: order_status(order["order_id"]) is OrderStatus.complete)

    with SessionLocal() as session:
        outcomes = list(session.scalars(select(Assignment.outcome).where(Assignment.task_id == task_id).order_by(Assignment.id)))
    assert outcomes == [AssignmentOutcome.failed, AssignmentOutcome.completed]
    assert fresh(Task, task_id).location_id in set(bins.values()) - {first_bin}
    assert client.get("/api/v1/exceptions", params={"open": "true"}).json()["count"] == 0


def test_short_bin_becomes_a_stockout_and_waits_for_the_supervisor(client, db, floor, stock):
    bins = stock({(1, 1): 3})
    floor.worker(0, 0)
    clock = FakeClock()
    sim = Simulator(client, SimulatorConfig(seed=7, pick_seconds=1, **QUIET), clock=clock)
    order = place_order(client, floor, "SHORT-1", qty=3)
    task_id = order_tasks(order)[0]["task_id"]
    # The system believed 3 were there, but one is missing.
    row = db.scalar(select(Inventory).where(Inventory.location_id == bins[(1, 1)]))
    row.qty_on_hand = 2
    db.commit()

    drive(sim, clock, until=lambda: fresh(Task, task_id).status is TaskStatus.exception)

    items = client.get("/api/v1/exceptions", params={"open": "true"}).json()["items"]
    assert [(e["type"], e["qty_found"], e["rerouted_to_location_id"]) for e in items] == [("stockout", 2, None)]
    assert order_status(order["order_id"]) is OrderStatus.open


def test_downed_worker_recovers_after_the_delay_and_the_order_finishes(client, floor, stock):
    stock({(1, 1): 5})
    worker = floor.worker(0, 0)
    clock = FakeClock()
    sim = Simulator(client, SimulatorConfig(seed=7, pick_seconds=1, recovery_seconds=20, **QUIET), clock=clock)
    order = place_order(client, floor, "DOWN-1")
    sim.force(order_tasks(order)[0]["task_id"], "worker_down")

    status = lambda: fresh(Worker, worker.id).status  # noqa: E731
    drive(sim, clock, until=lambda: status() is WorkerStatus.down, seconds_per_step=1)
    went_down_at = clock.now
    drive(sim, clock, until=lambda: status() is not WorkerStatus.down, seconds_per_step=1)

    assert 20 <= clock.now - went_down_at <= 22
    drive(sim, clock, until=lambda: order_status(order["order_id"]) is OrderStatus.complete)
    assert client.get("/api/v1/exceptions", params={"open": "true"}).json()["count"] == 0


def test_a_conflict_is_skipped_instead_of_stopping_the_simulator(client, floor, stock):
    stock({(1, 1): 5})
    floor.worker(0, 0)
    clock = FakeClock()
    sim = Simulator(client, SimulatorConfig(seed=7, pick_seconds=1, **QUIET), clock=clock)
    order = place_order(client, floor, "RACE-1")
    assign()
    active = client.get(ACTIVE_URL).json()["items"][0]
    client.post(f"/api/v1/tasks/{active['task_id']}/pick", json={"assignment_id": active["assignment_id"]})

    action = sim._finish(active, "pick", now=0.0)

    assert (action.ok, action.detail) == (False, "assignment_not_active")
    assert order_status(order["order_id"]) is OrderStatus.complete


def test_same_seed_gives_the_same_outcomes():
    assignment = {"worker_x": 0, "worker_y": 0, "location_x": 1, "location_y": 1, "worker_speed": 1.0}
    config = dict(seed=5, p_stockout=0.2, p_jam=0.2, p_worker_down=0.2)

    a, b = (Simulator(None, SimulatorConfig(**config)) for _ in range(2))
    seq_a = [a._plan(assignment, 0.0).outcome for _ in range(50)]
    seq_b = [b._plan(assignment, 0.0).outcome for _ in range(50)]

    assert seq_a == seq_b
    assert {"pick", "stockout", "jam", "worker_down"} <= set(seq_a)


@pytest.mark.parametrize(
    "bad", [{"tick_seconds": 0}, {"worker_speed": -1}, {"p_jam": -0.1}, {"p_stockout": 0.6, "p_jam": 0.6}]
)
def test_bad_config_is_rejected(bad):
    with pytest.raises(ValueError):
        SimulatorConfig(**bad)


def test_run_survives_an_api_outage(monkeypatch):
    sim = Simulator(None, SimulatorConfig(tick_seconds=0.001, **QUIET))
    ticks = []

    def flaky_tick():
        ticks.append(1)
        if len(ticks) == 1:
            raise httpx.ConnectError("server reloading")
        if len(ticks) == 2:
            request = httpx.Request("GET", "http://test/x")
            raise ApiCallError(httpx.Response(500, json={"detail": "boom", "code": "internal"}, request=request))

    monkeypatch.setattr(sim, "tick", flaky_tick)

    sim.run(max_ticks=3)

    assert len(ticks) == 3


# --- trigger ------------------------------------------------------------------------------------------


def test_trigger_raises_on_the_active_assignment(client, floor, stock):
    stock({(1, 1): 5, (2, 2): 5})
    floor.worker(0, 0)
    order = place_order(client, floor, "TRIG-1")
    assign()
    task_id = order_tasks(order)[0]["task_id"]

    result = trigger_exception(client, task_id, "stockout")

    assert (result["type"], result["task_status"]) == ("stockout", "open")
    with pytest.raises(ValueError):
        trigger_exception(client, task_id, "jam")  # no active assignment any more


# --- GET /simulation/assignments/active ---------------------------------------------------------------


def test_active_assignments_list_what_the_simulator_needs(client, floor, stock):
    bins = stock({(4, 5): 7})
    worker = floor.worker(0, 0)
    order = place_order(client, floor, "ACT-1", qty=2)
    made = assign()[0]

    body = client.get(ACTIVE_URL).json()

    assert body["count"] == 1
    item = body["items"][0]
    assert item.pop("assigned_at").endswith("Z")
    assert item == {
        "assignment_id": made.assignment_id,
        "task_id": order_tasks(order)[0]["task_id"],
        "order_id": order["order_id"],
        "worker_id": worker.id,
        "worker_x": 0,
        "worker_y": 0,
        "worker_speed": 1.0,
        "location_id": bins[(4, 5)],
        "location_x": 4,
        "location_y": 5,
        "sku_code": "SKU-T",
        "qty": 2,
        "bin_on_hand": 7,
    }


def test_active_assignments_skip_ended_ones(client, floor, stock):
    stock({(1, 1): 5})
    floor.worker(0, 0)
    place_order(client, floor, "ACT-2")
    made = assign()[0]
    client.post(f"/api/v1/tasks/{made.task_id}/pick", json={"assignment_id": made.assignment_id})

    assert client.get(ACTIVE_URL).json() == {"items": [], "count": 0}


def test_bin_with_no_inventory_row_holds_zero(client, floor):
    task = floor.task(1, 1, status=TaskStatus.assigned)
    floor.assign(task, floor.worker(0, 0, status=WorkerStatus.busy))

    assert client.get(ACTIVE_URL).json()["items"][0]["bin_on_hand"] == 0


# --- client and CLI -----------------------------------------------------------------------------------


def test_client_defaults_to_the_backend_port(monkeypatch):
    monkeypatch.delenv("SIM_API_URL", raising=False)

    with client_from_env() as client:
        assert str(client.base_url).rstrip("/") == "http://localhost:8080"
        assert "authorization" not in client.headers


def test_client_url_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("SIM_API_URL", "http://example.test:9000")

    with client_from_env() as client:
        assert str(client.base_url).rstrip("/") == "http://example.test:9000"


def test_cli_flags_override_the_config():
    args = cli.build_parser().parse_args(["run", "--tick", "2", "--p-jam", "0.5", "--seed", "9", "--ticks", "1"])

    config = cli._simulator_config(args)

    assert (config.tick_seconds, config.p_jam, config.seed) == (2.0, 0.5, 9)


def test_cli_rejects_a_bad_config():
    assert cli.main(["run", "--tick", "0"]) == 2


def test_cli_has_only_run_and_trigger():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(["seed"])


def test_no_events_are_written_by_a_quiet_tick(client, db):
    sim = Simulator(client, SimulatorConfig(seed=1, **QUIET), clock=FakeClock())

    assert sim.tick() == []
    assert db.scalar(select(func.count()).select_from(Event)) == 0

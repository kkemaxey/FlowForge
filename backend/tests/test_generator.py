"""The order generator: its seeded stream, intake outcomes, out-of-stock tracking, and the API."""
import time
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from app.core.database import SessionLocal
from app.main import app
from app.modules.generator.service import Generator, OrderStream
from app.modules.orders.models import Order
from app.modules.orders.schemas import OrderCreate, OrderLineIn
from app.modules.simulation.models import SimRun
from app.modules.warehouse.models import Inventory, Location, LocationKind, Sku

URL = "/api/v1/generator"


@pytest.fixture
def shoes(db):
    """Shoe -> pairs on hand, one bin each. Returns {sku_code: location_id}."""
    stock = {"SKU-A": 50, "SKU-B": 50, "SKU-C": 50, "SKU-LOW": 2, "SKU-NONE": 0}
    bins = {}
    for x, (code, qty) in enumerate(stock.items()):
        sku = Sku(code=code, name=code)
        location = Location(x=x, y=1, kind=LocationKind.storage)
        db.add_all([sku, location])
        db.flush()
        db.add(Inventory(location_id=location.id, sku_id=sku.id, qty_on_hand=qty))
        bins[code] = location.id
    run = SimRun(algorithm="greedy_v1", seed=1, order_rate=1.0)
    db.add(run)
    db.commit()
    bins["run_id"] = run.id
    return bins


@pytest.fixture
def live_client(db):
    """A client whose event loop stays up for the whole test, as in the real server, so the
    generator's background task keeps running between requests. Exiting stops the generator."""
    with TestClient(app) as client:
        yield client


def order(ref, *lines, run_id=None):
    return OrderCreate(
        external_ref=ref, run_id=run_id, lines=[OrderLineIn(sku_code=code, qty=qty) for code, qty in lines]
    )


def orders_in_db(db, run_id=None):
    db.rollback()
    query = select(Order)
    if run_id is not None:
        query = query.where(Order.run_id == run_id)
    return db.scalars(query).all()


# --- the seeded stream (no database) -------------------------------------------------------------

CODES = [f"SKU-{i:04d}" for i in range(1, 21)]


def take(stream, n):
    return [(stream.next_gap(), [(l.sku_code, l.qty) for l in stream.next_lines()]) for _ in range(n)]


def test_same_seed_gives_same_stream():
    assert take(OrderStream(480, 6, CODES), 50) == take(OrderStream(480, 6, list(reversed(CODES))), 50)


def test_different_seeds_give_different_streams():
    assert take(OrderStream(1, 6, CODES), 20) != take(OrderStream(2, 6, CODES), 20)


def test_orders_have_one_to_three_different_shoes_of_one_to_three_pairs():
    for _, lines in take(OrderStream(7, 6, CODES), 300):
        codes = [code for code, _ in lines]
        assert 1 <= len(codes) <= 3
        assert len(set(codes)) == len(codes)
        assert all(code in CODES for code in codes)
        assert all(1 <= qty <= 3 for _, qty in lines)


def test_gaps_average_the_order_rate():
    gaps = [gap for gap, _ in take(OrderStream(3, 6, CODES), 2000)]  # 6/min -> 10 s apart on average
    assert 9 < sum(gaps) / len(gaps) < 11


# --- intake outcomes and out-of-stock tracking ---------------------------------------------------


def test_accepted_order_is_counted(db, shoes):
    gen = Generator()

    gen.place_order(order("G-1", ("SKU-A", 2)))

    assert (gen.created, gen.rejected, gen.out_of_stock) == (1, 0, {})
    assert len(orders_in_db(db)) == 1


def test_empty_shoe_is_rejected_and_listed(db, shoes):
    gen = Generator()

    gen.place_order(order("G-1", ("SKU-A", 1), ("SKU-NONE", 1)))

    assert (gen.created, gen.rejected) == (0, 1)
    assert gen.out_of_stock == {"SKU-NONE": 1}
    assert orders_in_db(db) == []  # whole order rejected, nothing written


def test_listed_shoe_counts_every_order_it_costs(db, shoes):
    gen = Generator()

    for n in range(3):
        gen.place_order(order(f"G-{n}", ("SKU-NONE", 1)))

    assert gen.out_of_stock == {"SKU-NONE": 3}


def test_low_shoe_still_sells_smaller_orders(db, shoes):
    """Option A (live check): 2 pairs left -> an order for 3 is rejected, but 1 and 1 go through."""
    gen = Generator()

    gen.place_order(order("G-1", ("SKU-LOW", 3)))
    assert (gen.rejected, gen.out_of_stock) == (1, {})  # not listed: it still has 2 pairs

    gen.place_order(order("G-2", ("SKU-LOW", 1)))
    gen.place_order(order("G-3", ("SKU-LOW", 1)))
    assert gen.created == 2

    gen.place_order(order("G-4", ("SKU-LOW", 1)))
    assert gen.out_of_stock == {"SKU-LOW": 1}  # now truly empty


def test_restocked_shoe_drops_off_the_list_and_sells_again(db, shoes):
    gen = Generator()
    gen.place_order(order("G-1", ("SKU-NONE", 1)))
    gen.refresh_out_of_stock()
    assert gen.out_of_stock == {"SKU-NONE": 1}  # still empty: stays listed

    with SessionLocal() as s:  # restock
        s.execute(update(Inventory).where(Inventory.location_id == shoes["SKU-NONE"]).values(qty_on_hand=10))
        s.commit()
    gen.refresh_out_of_stock()

    assert gen.out_of_stock == {}
    gen.place_order(order("G-2", ("SKU-NONE", 1)))
    assert gen.created == 1


def test_refresh_handles_bins_with_more_reserved_than_on_hand(db, shoes):
    """After a pick-time stockout on_hand can fall below reserved; that must not break the query."""
    gen = Generator()
    gen.place_order(order("G-1", ("SKU-NONE", 1)))
    with SessionLocal() as s:
        s.execute(
            update(Inventory).where(Inventory.location_id == shoes["SKU-NONE"]).values(qty_on_hand=1, qty_reserved=3)
        )
        s.commit()

    gen.refresh_out_of_stock()

    assert gen.out_of_stock == {"SKU-NONE": 1}


# --- the API and background task -----------------------------------------------------------------


def test_off_until_started(live_client, shoes):
    status = live_client.get(URL).json()

    assert status["running"] is False
    time.sleep(0.3)
    assert orders_in_db(SessionLocal()) == []


def test_start_creates_a_sim_run_and_stop_ends_it(live_client, db, shoes):
    started = live_client.post(f"{URL}/start", json={"order_rate": 30, "seed": 480}).json()

    assert started["running"] is True
    assert (started["order_rate"], started["seed"]) == (30, 480)
    assert started["started_at"].endswith("Z")
    run = SessionLocal().get(SimRun, started["run_id"])
    assert (run.algorithm, run.seed, run.order_rate, run.ended_at) == ("greedy_v1", 480, 30, None)

    stopped = live_client.post(f"{URL}/stop").json()

    assert stopped["running"] is False
    assert stopped["run_id"] == started["run_id"]  # last run stays visible after stopping
    assert SessionLocal().get(SimRun, started["run_id"]).ended_at is not None


def test_second_start_is_409(live_client, shoes):
    live_client.post(f"{URL}/start", json={"order_rate": 1})

    response = live_client.post(f"{URL}/start", json={"order_rate": 1})

    assert response.status_code == 409
    assert response.json()["code"] == "generator_running"


def test_stop_when_idle_is_a_no_op(live_client, shoes):
    response = live_client.post(f"{URL}/stop")

    assert response.status_code == 200
    assert response.json()["running"] is False


def test_seed_is_chosen_and_recorded_when_omitted(live_client, shoes):
    started = live_client.post(f"{URL}/start").json()

    assert isinstance(started["seed"], int)
    assert started["order_rate"] == 6
    assert SessionLocal().get(SimRun, started["run_id"]).seed == started["seed"]


def test_no_skus_is_409(live_client, db):
    response = live_client.post(f"{URL}/start")

    assert response.status_code == 409
    assert response.json()["code"] == "no_skus"
    assert live_client.get(URL).json()["running"] is False


@pytest.mark.parametrize("body", [{"order_rate": 0}, {"order_rate": 601}, {"seed": -1}], ids=str)
def test_bad_start_body_is_422(live_client, shoes, body):
    response = live_client.post(f"{URL}/start", json=body)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_streams_orders_into_intake_until_stopped(live_client, db, shoes):
    started = live_client.post(f"{URL}/start", json={"order_rate": 600, "seed": 1}).json()  # ~10 per second
    time.sleep(1.5)
    status = live_client.post(f"{URL}/stop").json()

    sent = status["created"] + status["rejected"]
    assert 4 <= sent <= 40
    assert status["errors"] == 0

    generated = orders_in_db(db, started["run_id"])
    assert len(generated) == status["created"]
    for o in generated:
        assert o.external_ref.startswith(f"GEN-{started['run_id']}-")
        assert o.priority == 0
        assert timedelta(minutes=29) < o.due_at - o.created_at <= timedelta(minutes=30)

    time.sleep(0.3)  # stopped means stopped
    assert len(orders_in_db(db, started["run_id"])) == len(generated)


def test_status_lists_empty_shoes_during_a_run(live_client, shoes):
    live_client.post(f"{URL}/start", json={"order_rate": 600, "seed": 2})
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        listed = [s["sku_code"] for s in live_client.get(URL).json()["out_of_stock"]]
        if "SKU-NONE" in listed:
            break
        time.sleep(0.05)
    live_client.post(f"{URL}/stop")

    assert "SKU-NONE" in listed


def test_app_shutdown_stops_the_generator_and_ends_the_run(db, shoes):
    with TestClient(app) as client:
        run_id = client.post(f"{URL}/start", json={"order_rate": 1}).json()["run_id"]

    with SessionLocal() as s:
        assert s.get(SimRun, run_id).ended_at is not None
        assert s.scalar(select(func.count()).select_from(SimRun).where(SimRun.ended_at.is_(None))) == 1  # fixture's

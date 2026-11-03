import json

import httpx
import pytest
from sqlalchemy import select

from app.modules.simulation.models import Sku
from app.modules.simulation.order_generator import OrderGenerator
from app.modules.simulation.seed import SeedConfig, seed_database
from tests.sim_fixtures import api, db, db_engine, session_factory  # noqa: F401


@pytest.fixture
def warehouse(db):
    return seed_database(db, SeedConfig(seed=11, width=13, height=12, skus=20, workers=2, robots=1, low_stock_skus=2))


def test_orders_use_only_stocked_skus_with_valid_lines(api, db, warehouse):
    generator = OrderGenerator(api, seed=3, clock_ms=lambda: 1000)
    generator.refresh_stock()
    seeded = set(db.scalars(select(Sku.sku_code)))

    orders = [generator.build_order() for _ in range(100)]

    for order in orders:
        codes = [line["sku_code"] for line in order["lines"]]
        assert 1 <= len(codes) <= 4
        assert len(set(codes)) == len(codes), "no SKU twice in one order"
        assert set(codes) <= seeded
        for line in order["lines"]:
            assert 1 <= line["qty"] <= min(5, generator.stock[line["sku_code"]])
    assert {len(o["lines"]) for o in orders} == {1, 2, 3, 4}


def test_external_refs_are_unique_and_tied_to_the_run(api, db, warehouse):
    generator = OrderGenerator(api, seed=3, clock_ms=lambda: 1000)
    generator.refresh_stock()

    refs = [generator.build_order()["external_ref"] for _ in range(50)]

    assert len(set(refs)) == 50
    assert refs[0] == f"sim-r{warehouse.run_id}-1000-00001"


def test_same_seed_gives_same_orders(api, db, warehouse):
    batches = []
    for _ in range(2):
        generator = OrderGenerator(api, seed=9, clock_ms=lambda: 1000)
        generator.refresh_stock()
        batches.append([generator.build_order() for _ in range(20)])
    assert batches[0] == batches[1]


def fake_api(stock: list[dict], posted: list[dict]) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/simulation/runs/active":
            return httpx.Response(404, json={"detail": "No simulation run is active", "code": "no_active_run"})
        if request.url.path == "/api/v1/inventory/skus":
            return httpx.Response(200, json=stock)
        if request.url.path == "/api/v1/orders" and request.method == "POST":
            posted.append(json.loads(request.content))
            return httpx.Response(201, json={"order_id": len(posted)})
        return httpx.Response(404)

    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://test")


def test_post_one_sends_the_order_to_intake():
    posted: list[dict] = []
    generator = OrderGenerator(fake_api([{"sku_code": "SKU-0001", "available": 2}], posted), seed=1, clock_ms=lambda: 5)

    order = generator.post_one()

    assert posted == [order]
    assert order["external_ref"] == "sim-r0-5-00001"
    assert order["lines"] == [{"sku_code": "SKU-0001", "qty": order["lines"][0]["qty"]}]
    assert order["lines"][0]["qty"] in (1, 2)


def test_skips_when_nothing_is_in_stock():
    posted: list[dict] = []
    generator = OrderGenerator(fake_api([], posted), seed=1)

    assert generator.post_one() is None
    assert posted == []

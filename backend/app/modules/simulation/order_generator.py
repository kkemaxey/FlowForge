"""Posts synthetic orders to POST /api/v1/orders at a steady rate.

Lines (1-4 distinct SKUs) are drawn only from SKUs that currently have unreserved stock.
external_ref is "sim-r{run_id}-{start_ms}-{n:05d}": unique per generator session even across
restarts, because intake is idempotent on external_ref and would silently drop repeats.

The payload shape {"external_ref", "lines": [{"sku_code", "qty"}]} must match orders intake (Kanayo).
"""
import logging
import random
import time
from collections.abc import Callable

import httpx

from app.modules.simulation.client import ApiCallError, checked

log = logging.getLogger("flowforge.orders")

API = "/api/v1"
# At most 4 lines per order and 5 units per line.
MAX_LINES = 4
MAX_QTY = 5


class OrderGenerator:
    def __init__(self, client: httpx.Client, *, seed: int | None = None, clock_ms: Callable[[], int] | None = None) -> None:
        # HTTP client for the API.
        self.client = client
        # Own random generator: the same seed produces the same sequence of orders.
        self.rng = random.Random(seed)
        # When this generator started, in milliseconds. Part of every external_ref so a restarted
        # generator never reuses an old ref. Tests pass clock_ms to get a fixed value.
        self.started_ms = (clock_ms or (lambda: int(time.time() * 1000)))()
        # How many orders built so far (the last part of the ref: 00001, 00002, ...).
        self.count = 0
        # The run these orders belong to (None if no run is active).
        self.run_id = self._active_run_id()
        # sku_code -> units available, refreshed before each order.
        self.stock: dict[str, int] = {}

    def _active_run_id(self) -> int | None:
        """Ask the API for the active run; None if there isn't one (404)."""
        try:
            return checked(self.client.get(f"{API}/simulation/runs/active")).json()["run_id"]
        except ApiCallError as exc:
            if exc.status_code == 404:
                return None
            raise

    def refresh_stock(self) -> None:
        """Load which SKUs have free stock right now, and how much."""
        self.stock = {s["sku_code"]: s["available"] for s in checked(self.client.get(f"{API}/inventory/skus")).json()}

    def build_order(self) -> dict | None:
        """Next order payload, or None if no SKU has stock. Draws only from self.stock."""
        if not self.stock:
            return None
        # Sorted so the random choices below don't depend on dict ordering (keeps runs repeatable).
        codes = sorted(self.stock)
        lines = [
            # Quantity 1..5, but never more than the SKU has available.
            {"sku_code": code, "qty": self.rng.randint(1, min(MAX_QTY, self.stock[code]))}
            # Pick 1-4 *different* SKUs (sample never repeats an item).
            for code in self.rng.sample(codes, self.rng.randint(1, min(MAX_LINES, len(codes))))
        ]
        self.count += 1
        # e.g. "sim-r2-1793666899904-00001": run 2, generator start time, order number 1.
        ref = f"sim-r{self.run_id or 0}-{self.started_ms}-{self.count:05d}"
        return {"external_ref": ref, "lines": lines}

    def post_one(self) -> dict | None:
        """Build one order from current stock and send it to intake. Returns it, or None if skipped."""
        self.refresh_stock()
        order = self.build_order()
        if order is None:
            log.warning("No SKU has unreserved stock; skipping")
            return None
        checked(self.client.post(f"{API}/orders", json=order))
        log.info("posted %s with %d line(s)", order["external_ref"], len(order["lines"]))
        return order

    def run(self, per_minute: float, count: int | None = None) -> None:
        """Post orders at a steady rate until `count` are sent (or forever if count is None)."""
        if per_minute <= 0:
            raise ValueError("rate must be > 0 orders per minute")
        # Seconds between orders, e.g. 6 per minute -> one every 10 seconds.
        interval = 60.0 / per_minute
        posted = 0
        while count is None or posted < count:
            started = time.monotonic()
            if self.post_one() is not None:
                posted += 1
            # Wait out the rest of the interval.
            time.sleep(max(0.0, interval - (time.monotonic() - started)))

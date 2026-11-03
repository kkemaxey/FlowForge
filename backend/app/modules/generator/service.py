"""Order generator: streams random shoe orders into intake at a configurable rate.

Runs as a background task inside the backend, started and stopped through the API. Each start
creates a new sim_runs row, and every order it sends is tagged with that run_id so runs can be
measured separately.

Orders pick from all shoes, like real customers. Intake decides: an order it can't cover is
rejected with insufficient_stock (nothing written) and counted. A shoe with 0 unreserved pairs
left goes on the out_of_stock list; a shoe with a few pairs left still sells smaller orders.
Listed shoes are re-checked every RESTOCK_CHECK_SECONDS and drop off once they have stock again,
so a restock is picked up without restarting the generator.

The same seed gives the same order stream (same gaps, shoes, and quantities), since what gets
generated doesn't depend on stock. Only accepted vs rejected depends on the stock at the time.
"""
import asyncio
import logging
import random
import threading
from datetime import datetime, timedelta
from time import monotonic

from sqlalchemy import Integer, cast, func, select

from app.core.database import SessionLocal, utcnow
from app.core.errors import ApiError
from app.modules.assignment.loop import ALGORITHM
from app.modules.generator.schemas import GeneratorStatus, OutOfStockOut
from app.modules.orders import service as orders_service
from app.modules.orders.schemas import OrderCreate, OrderLineIn
from app.modules.simulation.models import SimRun
from app.modules.warehouse.models import Inventory, Sku

logger = logging.getLogger("uvicorn.error").getChild("generator")

MAX_SHOES_PER_ORDER = 3
MAX_PAIRS_PER_LINE = 3
DUE_IN = timedelta(minutes=30)
RESTOCK_CHECK_SECONDS = 5.0


class OrderStream:
    """Seeded source of order timing and contents. Deterministic for a given seed."""

    def __init__(self, seed: int, order_rate: float, sku_codes: list[str]) -> None:
        self._rng = random.Random(seed)
        self._per_second = order_rate / 60
        self._sku_codes = sorted(sku_codes)

    def next_gap(self) -> float:
        """Seconds until the next order: random gaps that average order_rate per minute."""
        return self._rng.expovariate(self._per_second)

    def next_lines(self) -> list[OrderLineIn]:
        shoes = self._rng.sample(self._sku_codes, self._rng.randint(1, min(MAX_SHOES_PER_ORDER, len(self._sku_codes))))
        return [OrderLineIn(sku_code=code, qty=self._rng.randint(1, MAX_PAIRS_PER_LINE)) for code in shoes]


class Generator:
    def __init__(self) -> None:
        self._lock = threading.Lock()  # counters are written from a worker thread, read by the API
        self._task: asyncio.Task | None = None
        self._stop: asyncio.Event | None = None
        self._starting = False
        self._stream: OrderStream | None = None
        self.run_id: int | None = None
        self.order_rate: float | None = None
        self.seed: int | None = None
        self.started_at: datetime | None = None
        self._reset_counters()

    def _reset_counters(self) -> None:
        with self._lock:
            self.sent = 0
            self.created = 0
            self.rejected = 0
            self.errors = 0
            self.out_of_stock: dict[str, int] = {}

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    # --- control (called from the API, on the event loop) ----------------------------------------

    async def start(self, order_rate: float, seed: int | None) -> None:
        if self.running or self._starting:
            raise ApiError(409, "generator_running", f"Generator already running (run {self.run_id}); stop it first")
        self._starting = True  # blocks a second start while this one waits on the database
        try:
            if seed is None:
                seed = random.SystemRandom().randrange(2**31)
            run_id, started_at, sku_codes = await asyncio.to_thread(self._create_run, order_rate, seed)
            self._reset_counters()
            self.run_id, self.order_rate, self.seed, self.started_at = run_id, order_rate, seed, started_at
            self._stream = OrderStream(seed, order_rate, sku_codes)
            self._stop = asyncio.Event()
            self._task = asyncio.create_task(self._run(self._stop))
        finally:
            self._starting = False
        logger.info("generator started: run %d, %s orders/min, seed %d", run_id, order_rate, seed)

    async def stop(self) -> None:
        """Stop the current run and record its end. Does nothing if not running."""
        if self._task is None:
            return
        task, self._task = self._task, None
        self._stop.set()
        await task
        await asyncio.to_thread(self._end_run, self.run_id)
        logger.info("generator stopped: run %d, %d created, %d rejected", self.run_id, self.created, self.rejected)

    def status(self) -> GeneratorStatus:
        with self._lock:
            out_of_stock = [
                OutOfStockOut(sku_code=code, rejected_orders=count) for code, count in sorted(self.out_of_stock.items())
            ]
            return GeneratorStatus(
                running=self.running,
                run_id=self.run_id,
                order_rate=self.order_rate,
                seed=self.seed,
                started_at=self.started_at,
                created=self.created,
                rejected=self.rejected,
                errors=self.errors,
                out_of_stock=out_of_stock,
            )

    # --- the loop --------------------------------------------------------------------------------

    async def _run(self, stop: asyncio.Event) -> None:
        last_restock_check = monotonic()
        while True:
            try:
                await asyncio.wait_for(stop.wait(), timeout=self._stream.next_gap())
                return  # stop was requested during the wait
            except TimeoutError:
                pass
            try:
                # Database work is blocking; keep it off the event loop that serves requests.
                await asyncio.to_thread(self.generate_one)
                if monotonic() - last_restock_check >= RESTOCK_CHECK_SECONDS:
                    await asyncio.to_thread(self.refresh_out_of_stock)
                    last_restock_check = monotonic()
            except Exception:
                logger.exception("generator step failed; continuing")
                with self._lock:
                    self.errors += 1

    def generate_one(self) -> None:
        with self._lock:
            self.sent += 1
            n = self.sent
        self.place_order(
            OrderCreate(
                external_ref=f"GEN-{self.run_id}-{n}",
                run_id=self.run_id,
                priority=0,
                due_at=utcnow() + DUE_IN,
                lines=self._stream.next_lines(),
            )
        )

    def place_order(self, payload: OrderCreate) -> None:
        """Send one order through intake and record the outcome."""
        with SessionLocal() as session:
            try:
                orders_service.create_order(session, payload)
            except orders_service.InsufficientStock as rejection:
                with self._lock:
                    self.rejected += 1
                    # Only a shoe that is truly empty is "out"; one with a few pairs left still sells.
                    if rejection.available == 0 or rejection.sku_code in self.out_of_stock:
                        self.out_of_stock[rejection.sku_code] = self.out_of_stock.get(rejection.sku_code, 0) + 1
                return
        with self._lock:
            self.created += 1

    def refresh_out_of_stock(self) -> None:
        """Drop shoes from the out_of_stock list once they have unreserved stock again."""
        with self._lock:
            listed = list(self.out_of_stock)
        if not listed:
            return
        # Signed arithmetic: qty columns are UNSIGNED, and on_hand can drop below reserved after a stockout.
        unreserved = func.greatest(cast(Inventory.qty_on_hand, Integer) - cast(Inventory.qty_reserved, Integer), 0)
        with SessionLocal() as session:
            available = dict(
                session.execute(
                    select(Sku.code, func.coalesce(func.sum(unreserved), 0))
                    .outerjoin(Inventory, Inventory.sku_id == Sku.id)
                    .where(Sku.code.in_(listed))
                    .group_by(Sku.code)
                ).all()
            )
        with self._lock:
            for code in listed:
                if available.get(code, 0) > 0:
                    self.out_of_stock.pop(code, None)

    # --- database bookkeeping --------------------------------------------------------------------

    @staticmethod
    def _create_run(order_rate: float, seed: int) -> tuple[int, datetime, list[str]]:
        with SessionLocal() as session:
            sku_codes = list(session.scalars(select(Sku.code)))
            if not sku_codes:
                raise ApiError(409, "no_skus", "No SKUs in the warehouse; run the seed script first")
            run = SimRun(algorithm=ALGORITHM, seed=seed, order_rate=order_rate)
            session.add(run)
            session.commit()
            return run.id, run.started_at, sku_codes

    @staticmethod
    def _end_run(run_id: int) -> None:
        with SessionLocal() as session:
            run = session.get(SimRun, run_id)
            if run is not None and run.ended_at is None:
                run.ended_at = utcnow()
                session.commit()


# One generator per backend process.
generator = Generator()

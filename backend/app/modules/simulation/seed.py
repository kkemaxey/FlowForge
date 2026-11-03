"""Synthetic warehouse data: grid map, SKUs, inventory, workforce, a simulation run and login users.

Layout on a W x H grid (x across, y down):
  y = 0         pick/pack stations
  y = 1, H-1    cross aisles
  aisle columns at x = 1, 4, 7, ... with bins on both sides (x-1 = L, x+1 = R), y = 2 .. H-2
Aisles are grouped two per zone: A1, A2, B1, B2, C1, ...
The default 10 x 10 grid gives 42 bins + 3 stations = 45 locations, sized for 25 SKUs.

All randomness comes from one random.Random(seed), so the same config always yields the same rows.
"""
import os
import random
import string
from dataclasses import asdict, dataclass, field

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

# Every table the seed writes to or wipes. They're imported (not redefined) from their owners' modules.
from app.modules.assignment.models import Assignment
from app.modules.auth.models import User
from app.modules.events.models import Event
from app.modules.orders.models import Order, OrderLine
from app.modules.simulation.models import Inventory, Location, SimRun, Sku, TaskException
from app.modules.tasks.models import Task
from app.modules.workforce.models import Worker

# Two aisles per zone: aisles 1-2 are zone A, 3-4 zone B, and so on.
AISLES_PER_ZONE = 2
# Word lists for made-up product names like "Eco Clamp 1".
ADJECTIVES = ["Blue", "Steel", "Compact", "Heavy", "Mini", "Large", "Eco", "Pro", "Smart", "Classic"]
NOUNS = ["Widget", "Bracket", "Cable", "Fastener", "Filter", "Valve", "Sensor", "Hinge", "Gasket", "Clamp"]

# Children before parents, so foreign keys hold at every step of a reset.
# (e.g. delete events and tasks before the orders they point at.)
RESET_ORDER = [Event, TaskException, Assignment, Task, OrderLine, Order, Inventory, Sku, Location, Worker, User, SimRun]


def _env_int(name: str, default: int) -> int:
    """Read an integer environment variable, or use the default if it isn't set."""
    return int(os.getenv(name, default))


@dataclass
class SeedConfig:
    """Every setting the seed uses. Each default can be overridden by an env var or a CLI flag."""

    # Random seed: the same seed always builds the same warehouse.
    seed: int = field(default_factory=lambda: _env_int("SEED_RANDOM_SEED", 480))
    # Grid size in cells.
    width: int = field(default_factory=lambda: _env_int("SEED_GRID_WIDTH", 10))
    height: int = field(default_factory=lambda: _env_int("SEED_GRID_HEIGHT", 10))
    # Number of products.
    skus: int = field(default_factory=lambda: _env_int("SEED_SKUS", 25))
    # Number of human pickers and robots.
    workers: int = field(default_factory=lambda: _env_int("SEED_WORKERS", 5))
    robots: int = field(default_factory=lambda: _env_int("SEED_ROBOTS", 5))
    # Number of pick/pack stations along the top row.
    stations: int = field(default_factory=lambda: _env_int("SEED_STATIONS", 3))
    # Share of SKUs stocked in 2-3 bins, and how many SKUs get 1-3 units total.
    multi_bin_share: float = 0.5
    low_stock_skus: int = field(default_factory=lambda: _env_int("SEED_LOW_STOCK_SKUS", 3))


@dataclass
class SeedResult:
    """What the seed created, so the CLI can print a summary."""

    run_id: int
    locations: int
    skus: int
    inventory_rows: int
    workers: int


class SeedError(Exception):
    """A seed problem the user can fix (grid too small, reset not allowed, ...)."""


def reset_allowed(db: Session) -> bool:
    """Only wipe SQLite, unless FLOWFORGE_ALLOW_RESET=1 says the target DB is disposable."""
    # dialect.name is "sqlite" for a local file, "mysql" for Cloud SQL.
    return db.get_bind().dialect.name == "sqlite" or os.getenv("FLOWFORGE_ALLOW_RESET") == "1"


def reset(db: Session) -> None:
    """Delete every row from every warehouse table (refuses on a real database unless allowed)."""
    if not reset_allowed(db):
        raise SeedError("Refusing to reset a non-SQLite database; set FLOWFORGE_ALLOW_RESET=1 to override")
    for model in RESET_ORDER:
        # DELETE FROM <table>, built by SQLAlchemy (no raw SQL strings).
        db.execute(delete(model))


def is_seeded(db: Session) -> bool:
    """True if the map already exists (any locations at all)."""
    return db.scalar(select(func.count()).select_from(Location)) > 0


def seed_database(db: Session, config: SeedConfig, *, reset_first: bool = False) -> SeedResult | None:
    """Seed everything in one transaction. Returns None (and changes nothing) if already seeded."""
    if reset_first:
        # --reset: wipe first, then reseed.
        reset(db)
    elif is_seeded(db):
        # Already seeded and no --reset: leave the data alone.
        return None

    # One random-number generator for everything, started from the seed, so results repeat exactly.
    rng = random.Random(config.seed)

    # 1. The map: stations and bins.
    stations, bins = _build_map(config)
    db.add_all(stations + bins)

    # 2. The products.
    skus = _build_skus(config, rng)
    db.add_all(skus)
    # flush sends the inserts now so every location and SKU gets its id (inventory needs those ids).
    db.flush()

    # 3. Stock: which SKU sits in which bin, and how many.
    inventory = _build_inventory(config, rng, skus, bins)
    db.add_all(inventory)

    # 4. Pickers and robots.
    workers = _build_workers(config, rng, stations)
    db.add_all(workers)

    # 5. A simulation run, recording the exact settings used.
    run = SimRun(seed=config.seed, config=asdict(config))
    db.add(run)
    # Save it all at once.
    db.commit()

    return SeedResult(
        run_id=run.id,
        locations=len(stations) + len(bins),
        skus=len(skus),
        inventory_rows=len(inventory),
        workers=len(workers),
    )


def _build_map(config: SeedConfig) -> tuple[list[Location], list[Location]]:
    """Lay out the stations (top row) and bins (both sides of each aisle)."""
    if config.width < 4 or config.height < 5:
        raise SeedError("Grid must be at least 4 x 5")
    # Stations spread evenly across row 0. On a 10-wide grid with 3 stations: x = 2, 5, 7.
    stations = [
        Location(code=f"ST-{i + 1}", zone="PK", x=config.width * (i + 1) // (config.stations + 1), y=0, kind="station")
        for i in range(config.stations)
    ]
    bins = []
    # Aisle columns every 3 cells: x = 1, 4, 7, ... (each leaves a bin column on either side).
    aisle_xs = range(1, config.width - 1, 3)
    for index, aisle_x in enumerate(aisle_xs):
        # Aisles 0-1 -> zone "A", 2-3 -> "B", ...
        zone = string.ascii_uppercase[index // AISLES_PER_ZONE]
        # Aisle name within the zone: "A1", "A2", "B1", ...
        aisle = f"{zone}{index % AISLES_PER_ZONE + 1}"
        # Bins run from row 2 to the second-last row (row 1 and the last row are cross aisles).
        for y in range(2, config.height - 1):
            # One bin on the left of the aisle (x-1) and one on the right (x+1).
            for side, x in (("L", aisle_x - 1), ("R", aisle_x + 1)):
                # Code = aisle-slot-side, e.g. "A1-01-L". Slot 01 is row 2.
                bins.append(Location(code=f"{aisle}-{y - 1:02d}-{side}", zone=zone, aisle=aisle, x=x, y=y, kind="bin"))
    return stations, bins


def _build_skus(config: SeedConfig, rng: random.Random) -> list[Sku]:
    """SKU-0001, SKU-0002, ... each with a random two-word name."""
    return [
        Sku(sku_code=f"SKU-{i:04d}", name=f"{rng.choice(ADJECTIVES)} {rng.choice(NOUNS)} {i}")
        for i in range(1, config.skus + 1)
    ]


def _build_inventory(config: SeedConfig, rng: random.Random, skus: list[Sku], bins: list[Location]) -> list[Inventory]:
    """Put every SKU into 1-3 bins. A few SKUs get almost no stock so stockouts happen naturally."""
    # Pick which SKUs (by position in the list) are deliberately low-stock.
    low_stock = set(rng.sample(range(len(skus)), min(config.low_stock_skus, len(skus))))
    # How many bins each SKU goes into: low-stock SKUs get 1; others get 2-3 about half the time.
    bin_counts = [
        1 if i in low_stock or rng.random() >= config.multi_bin_share else rng.randint(2, 3)
        for i in range(len(skus))
    ]
    # One SKU per bin, so we can't place more SKU/bin pairs than there are bins.
    if sum(bin_counts) > len(bins):
        raise SeedError(f"{sum(bin_counts)} bin slots needed but the grid only has {len(bins)} bins")

    # Randomly choose exactly as many distinct bins as we need.
    free_bins = rng.sample(bins, sum(bin_counts))
    rows = []
    for i, (sku, count) in enumerate(zip(skus, bin_counts)):
        for _ in range(count):
            # Low-stock SKUs: 1-3 units. Everything else: 20-120 units.
            on_hand = rng.randint(1, 3) if i in low_stock else rng.randint(20, 120)
            # pop() takes one bin off the list so no bin is used twice. Nothing reserved yet.
            rows.append(Inventory(sku_id=sku.id, location_id=free_bins.pop().id, on_hand=on_hand, reserved=0))
    return rows


def _build_workers(config: SeedConfig, rng: random.Random, stations: list[Location]) -> list[Worker]:
    """Human pickers and robots, all idle, starting near a random station."""

    def start_position() -> tuple[int, int]:
        # Within 2 cells left/right of a random station (kept inside the grid), in row 0 or 1.
        station = rng.choice(stations)
        return max(0, min(config.width - 1, station.x + rng.randint(-2, 2))), rng.randint(0, 1)

    workers = []
    for i in range(1, config.workers + 1):
        x, y = start_position()
        # Humans: "Picker 01", ... with a random speed of 1.0-1.5 grid cells per second.
        workers.append(Worker(name=f"Picker {i:02d}", kind="human", speed=round(rng.uniform(1.0, 1.5), 2), x=x, y=y, status="idle"))
    for i in range(1, config.robots + 1):
        x, y = start_position()
        # Robots: "Robot R1", ... always 2.0 cells per second.
        workers.append(Worker(name=f"Robot R{i}", kind="robot", speed=2.0, x=x, y=y, status="idle"))
    return workers


def ensure_login_user(db: Session, email: str, password: str, role: str) -> User:
    """Create the Firebase account if missing, then the matching users row. Safe to re-run."""
    # Imported here, not at the top, so seeding without Firebase never needs Firebase set up.
    from firebase_admin import auth

    from app.core.security import _firebase_app

    firebase = _firebase_app()
    try:
        # Already exists? Reuse it.
        account = auth.get_user_by_email(email, app=firebase)
    except auth.UserNotFoundError:
        # Otherwise create it. The password comes from an env var, never from code.
        account = auth.create_user(email=email, password=password, app=firebase)

    # Make sure our own users table has a row for that Firebase account.
    user = db.scalar(select(User).where(User.firebase_uid == account.uid))
    if user is None:
        user = User(firebase_uid=account.uid, email=email, role=role)
        db.add(user)
        db.commit()
    return user

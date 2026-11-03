"""Load demo warehouse data: grid, SKUs, inventory, workers, a supervisor, and one sim run.

Run inside the backend container after migrating:
    docker compose exec backend python -m app.seed

Deterministic (fixed random seed), so every teammate gets the same warehouse. Refuses to run
if locations already exist; wipe with `docker compose down -v` and re-migrate to start over.

Layout (10 x 10, x = column, y = row):
    y = 0          pick stations at x = 3, 6
    y = 1..8       storage racks in column pairs (1,2) (4,5) (7,8); columns 0, 3, 6, 9 are
                   walkways. Zone A is the front half (y = 1..4), zone B the back (y = 5..8).
                   Each rack pair is one aisle per zone: A1 A2 A3, B1 B2 B3.
    y = 9          open floor along the back, where the robots start
No docks or chargers for now: nothing in the MVP uses them.
"""
import random

from sqlalchemy import func, select

from app.core.database import SessionLocal
from app.modules.auth.models import User, UserRole
from app.modules.simulation.models import SimRun
from app.modules.warehouse.models import Inventory, Location, LocationKind, Sku
from app.modules.workforce.models import Worker, WorkerKind

SEED = 480
RACK_PAIRS = [(1, 2), (4, 5), (7, 8)]
STORAGE_ROWS = range(1, 9)

SKU_NAMES = [
    "Air Jordan 1 High", "Air Jordan 4", "Nike Air Force 1", "Nike Dunk Low", "Nike Air Max 90",
    "Adidas Samba", "Adidas Ultraboost", "Yeezy Boost 350", "New Balance 550", "New Balance 990v6",
    "Converse Chuck 70", "Vans Old Skool", "Puma Suede", "Asics Gel-Kayano 14", "Reebok Club C",
    "Salomon XT-6", "Hoka Clifton 9", "On Cloud 5", "Timberland 6-Inch Boot", "Crocs Classic Clog",
]

# SKUs stocked across several bins, so an order can split into tasks once a bin runs low.
SPLIT_SKUS = {"SKU-0001": (3, 4), "SKU-0002": (3, 3), "SKU-0003": (2, 5)}  # code: (bins, qty per bin)

# Scales every seeded quantity, so a demo doesn't run out of stock within minutes. Picks only ever
# remove stock and intake rejects what it can't cover, so this sets how long a demo can run.
STOCK_MULTIPLIER = 10

# Humans start along the front walkway near the pick stations; robots start at the back.
WORKERS = [
    ("Alex", WorkerKind.human, 0, 0),
    ("Sam", WorkerKind.human, 3, 0),
    ("Jordan", WorkerKind.human, 6, 0),
    ("Taylor", WorkerKind.human, 9, 0),
    ("Morgan", WorkerKind.human, 3, 4),
    ("Robo-1", WorkerKind.robot, 0, 9),
    ("Robo-2", WorkerKind.robot, 3, 9),
    ("Robo-3", WorkerKind.robot, 6, 9),
    ("Robo-4", WorkerKind.robot, 9, 9),
    ("Robo-5", WorkerKind.robot, 6, 5),
]


def build_locations() -> list[Location]:
    locations = []
    for aisle_no, columns in enumerate(RACK_PAIRS, start=1):
        for x in columns:
            for y in STORAGE_ROWS:
                zone = "A" if y <= 4 else "B"
                locations.append(
                    Location(x=x, y=y, kind=LocationKind.storage, zone=zone, aisle=f"{zone}{aisle_no}")
                )
    for x in (3, 6):
        locations.append(Location(x=x, y=0, kind=LocationKind.pick_station))
    return locations


def build_inventory(rng: random.Random, skus: list[Sku], bins: list[Location]) -> list[Inventory]:
    free_bins = bins[:]
    rng.shuffle(free_bins)
    rows = []
    for sku in skus:
        if sku.code in SPLIT_SKUS:
            bin_count, qty = SPLIT_SKUS[sku.code]
            quantities = [qty] * bin_count
        else:
            quantities = [rng.randint(10, 40) for _ in range(rng.randint(1, 2))]
        for qty in quantities:
            location = free_bins.pop()
            rows.append(Inventory(location_id=location.id, sku_id=sku.id, qty_on_hand=qty * STOCK_MULTIPLIER))
    return rows


def seed() -> None:
    rng = random.Random(SEED)
    with SessionLocal() as session:
        if session.scalar(select(func.count()).select_from(Location)):
            print("Seed skipped: locations already exist.")
            return

        locations = build_locations()
        skus = [Sku(code=f"SKU-{i:04d}", name=name) for i, name in enumerate(SKU_NAMES, start=1)]
        session.add_all(locations + skus)
        session.flush()  # assigns ids, needed for inventory rows

        storage = [loc for loc in locations if loc.kind is LocationKind.storage]
        inventory = build_inventory(rng, skus, storage)
        workers = [Worker(name=name, kind=kind, x=x, y=y) for name, kind, x, y in WORKERS]
        supervisor = User(firebase_uid="dev-supervisor", email="supervisor@flowforge.local", role=UserRole.supervisor)
        sim_run = SimRun(algorithm="greedy_v1", seed=SEED, order_rate=6.0)
        session.add_all(inventory + workers + [supervisor, sim_run])
        session.commit()

        print(
            f"Seeded {len(locations)} locations ({len(storage)} storage), {len(skus)} SKUs, "
            f"{len(inventory)} inventory rows, {len(workers)} workers, 1 supervisor, "
            f"sim run id {sim_run.id}."
        )


if __name__ == "__main__":
    seed()

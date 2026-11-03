"""Warehouse map, inventory, simulation runs and task exceptions.

Each class below is one database table. SQLAlchemy reads these classes to know what the
tables look like; Alembic reads them to generate the migration that creates the tables.
`Mapped[int]` is the Python type of a column; `mapped_column(...)` is how it is stored.
`Mapped[X | None]` means the column may be empty (NULL).
"""
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

# Base: every table class inherits from it so SQLAlchemy knows about the table.
# Timestamp: DATETIME(3) on MySQL (millisecond precision). utcnow: the current UTC time.
from app.core.database import Base, Timestamp, utcnow

# The allowed values for Location.kind and TaskException.type, kept in one place for reference.
LOCATION_KINDS = ("bin", "station")
EXCEPTION_TYPES = ("stockout", "jam", "worker_down")


class Location(Base):
    """One spot on the warehouse grid: a storage bin or a pick/pack station."""

    __tablename__ = "locations"  # the actual table name in the database

    # Auto-numbered unique id for each row (1, 2, 3, ...).
    id: Mapped[int] = mapped_column(primary_key=True)
    # Human-readable address. Bins look like "A1-07-L" (aisle, slot, side); stations like "ST-1".
    # unique=True: two locations can never share a code.
    code: Mapped[str] = mapped_column(String(32), unique=True)
    # Warehouse area: "A", "B", "C" for storage, "PK" for the packing stations.
    zone: Mapped[str] = mapped_column(String(8))
    # Which aisle the bin faces (e.g. "A1"). Empty for stations.
    aisle: Mapped[str | None] = mapped_column(String(8))
    # Grid position. The simulator uses these to compute walking distance.
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    # "bin" or "station".
    kind: Mapped[str] = mapped_column(String(16), default="bin")


class Sku(Base):
    """A product the warehouse stocks (SKU = stock keeping unit)."""

    __tablename__ = "skus"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The product code orders refer to, e.g. "SKU-0001". Must be unique.
    sku_code: Mapped[str] = mapped_column(String(32), unique=True)
    # Display name, e.g. "Eco Clamp 1".
    name: Mapped[str] = mapped_column(String(100))


class Inventory(Base):
    """Stock of one SKU in one bin. Available to promise = on_hand - reserved."""

    __tablename__ = "inventory"
    # Table-wide rules the database itself enforces:
    __table_args__ = (
        # A SKU appears at most once per bin (one row per SKU/bin pair).
        UniqueConstraint("sku_id", "location_id"),
        # Stock counts can never go negative.
        CheckConstraint("on_hand >= 0", name="ck_inventory_on_hand"),
        CheckConstraint("reserved >= 0", name="ck_inventory_reserved"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # ForeignKey: must match an existing skus.id. index=True makes lookups by SKU fast.
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id"), index=True)
    # Which bin this stock sits in (must match an existing locations.id).
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"), index=True)
    # Units physically in the bin.
    on_hand: Mapped[int] = mapped_column(Integer, default=0)
    # Units already promised to tasks that haven't been picked yet.
    reserved: Mapped[int] = mapped_column(Integer, default=0)
    # Bumped on every update; used to detect two requests changing the row at once.
    version: Mapped[int] = mapped_column(Integer, default=1)


class SimRun(Base):
    """One simulation session. Events and orders point at a run so metrics can be grouped per run."""

    __tablename__ = "sim_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The random seed used, so the run can be reproduced. Empty if none was given.
    seed: Mapped[int | None] = mapped_column(Integer)
    # The settings the run used (grid size, probabilities, ...), stored as JSON.
    config: Mapped[dict | None] = mapped_column(JSON)
    # When the run began. default=utcnow fills it in automatically on insert.
    started_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    # When the run ended. Empty means this is the active run.
    ended_at: Mapped[datetime | None] = mapped_column(Timestamp)


class TaskException(Base):
    """A stockout, jam or worker_down raised against an assignment. Open until resolved_at is set.

    Named TaskException (not Exception) so it doesn't clash with Python's built-in Exception.
    """

    __tablename__ = "exceptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Which simulation run this happened in.
    run_id: Mapped[int | None] = mapped_column(ForeignKey("sim_runs.id"), index=True)
    # "stockout", "jam" or "worker_down".
    type: Mapped[str] = mapped_column(String(16))
    # The task that hit the problem.
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), index=True)
    # The worker's assignment that was interrupted.
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"))
    # For a stockout: how many units the picker actually found in the bin.
    qty_found: Mapped[int | None] = mapped_column(Integer)
    # The bin where the problem happened.
    from_location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    # The bin the task was moved to. Empty if it couldn't be rerouted.
    rerouted_to_location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))
    # When it was reported.
    opened_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    # When it was dealt with. Empty = still waiting for the supervisor.
    resolved_at: Mapped[datetime | None] = mapped_column(Timestamp, index=True)

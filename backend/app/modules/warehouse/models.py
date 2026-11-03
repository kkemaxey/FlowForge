"""Static warehouse data: the location grid, the SKU catalog, and stock per bin."""
import enum

from sqlalchemy import Enum, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UnsignedInt


class LocationKind(str, enum.Enum):
    storage = "storage"
    pick_station = "pick_station"
    dock = "dock"
    charger = "charger"


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("x", "y", name="locations_x_y_unique"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    kind: Mapped[LocationKind] = mapped_column(
        Enum(LocationKind, name="location_kind", values_callable=lambda e: [m.value for m in e])
    )
    # Zone and aisle make bottleneck highlighting a simple GROUP BY later.
    zone: Mapped[str | None] = mapped_column(String(8))
    aisle: Mapped[str | None] = mapped_column(String(8))


class Sku(Base):
    __tablename__ = "skus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(128))


class Inventory(Base):
    """How much of each SKU sits in each bin.

    qty_reserved is raised when a task is created, so two orders can't both be sent for the
    last few units in a bin. Unreserved stock = qty_on_hand - qty_reserved.
    """

    __tablename__ = "inventory"
    __table_args__ = (Index("inventory_sku_id_index", "sku_id"),)

    location_id: Mapped[int] = mapped_column(Integer, ForeignKey("locations.id"), primary_key=True)
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("skus.id"), primary_key=True)
    qty_on_hand: Mapped[int] = mapped_column(UnsignedInt, default=0, server_default="0")
    qty_reserved: Mapped[int] = mapped_column(UnsignedInt, default=0, server_default="0")

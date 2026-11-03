"""Orders and their lines. One order_lines row per SKU on the order."""
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Enum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, BigId, Timestamp3, TinyInt, UnsignedInt, utcnow


class OrderStatus(str, enum.Enum):
    open = "open"
    complete = "complete"


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (Index("orders_status_due_at_index", "status", "due_at"),)

    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sim_runs.id"))
    # Unique so a retried intake request returns the existing order instead of a duplicate.
    external_ref: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, name="order_status", values_callable=lambda e: [m.value for m in e]),
        default=OrderStatus.open,
    )
    priority: Mapped[int] = mapped_column(TinyInt, default=0, server_default="0")
    expedited: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    due_at: Mapped[datetime | None] = mapped_column(Timestamp3)
    created_at: Mapped[datetime] = mapped_column(Timestamp3, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(Timestamp3)
    # Changed only by explicit compare-and-set updates, never by the ORM.
    version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    lines: Mapped[list["OrderLine"]] = relationship(
        back_populates="order", order_by="OrderLine.line_no", cascade="all, delete-orphan"
    )


class OrderLine(Base):
    __tablename__ = "order_lines"
    __table_args__ = (
        UniqueConstraint("order_id", "line_no", name="order_lines_order_id_line_no_unique"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    order_id: Mapped[int] = mapped_column(BigId, ForeignKey("orders.id"))
    line_no: Mapped[int] = mapped_column(SmallInteger)
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("skus.id"))
    qty_ordered: Mapped[int] = mapped_column(UnsignedInt)

    order: Mapped[Order] = relationship(back_populates="lines")

"""Order and OrderLine tables. Draft by Kendyn for the simulator and seed data; Kanayo to review."""
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, Timestamp, utcnow

ORDER_STATUSES = ("received", "in_progress", "complete")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Intake is idempotent on external_ref.
    external_ref: Mapped[str] = mapped_column(String(64), unique=True)
    run_id: Mapped[int | None] = mapped_column(ForeignKey("sim_runs.id"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="received")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(Timestamp)

    lines: Mapped[list["OrderLine"]] = relationship(back_populates="order")


class OrderLine(Base):
    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id"))
    qty: Mapped[int] = mapped_column(Integer)

    order: Mapped[Order] = relationship(back_populates="lines")

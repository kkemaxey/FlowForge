"""Pick task table. Draft by Kendyn for the simulator and exception flow; Kanayo to review."""
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, Timestamp, utcnow

# open -> assigned -> picked -> complete; assigned -> exception when no bin can cover a reroute.
TASK_STATUSES = ("open", "assigned", "picked", "complete", "exception")


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    order_line_id: Mapped[int] = mapped_column(ForeignKey("order_lines.id"))
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id"))
    # The bin this task picks from; its qty is reserved in that bin's inventory row.
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))
    qty: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow, onupdate=utcnow)

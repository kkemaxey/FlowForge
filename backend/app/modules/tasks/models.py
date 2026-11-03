"""Pick tasks. One row per (order line, location) pick; open rows are the work queue."""
import enum
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigId, Timestamp3, TinyInt, UnsignedInt, utcnow


class TaskStatus(str, enum.Enum):
    open = "open"
    assigned = "assigned"
    picked = "picked"
    exception = "exception"


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("tasks_location_id_status_index", "location_id", "status"),
        Index("tasks_order_id_status_index", "order_id", "status"),
        # Serves the work queue: WHERE status = 'open' ORDER BY priority DESC, created_at.
        Index("tasks_status_priority_created_at_index", "status", "priority", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigId, primary_key=True)
    order_id: Mapped[int] = mapped_column(BigId, ForeignKey("orders.id"))
    order_line_id: Mapped[int] = mapped_column(BigId, ForeignKey("order_lines.id"))
    sku_id: Mapped[int] = mapped_column(Integer, ForeignKey("skus.id"))
    location_id: Mapped[int] = mapped_column(Integer, ForeignKey("locations.id"))
    qty: Mapped[int] = mapped_column(UnsignedInt)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", values_callable=lambda e: [m.value for m in e]),
        default=TaskStatus.open,
    )
    # Copied from the order (and raised on expedite) so the work queue needs only one index.
    priority: Mapped[int] = mapped_column(TinyInt, default=0, server_default="0")
    # Changed only by the compare-and-set transition(), never by the ORM.
    version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(Timestamp3, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(Timestamp3, default=utcnow, onupdate=utcnow)

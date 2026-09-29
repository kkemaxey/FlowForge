"""Database table for pick tasks."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PickTaskRecord(Base):
    __tablename__ = "pick_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_ref: Mapped[str] = mapped_column(String(40), index=True)
    sku: Mapped[str] = mapped_column(String(40))
    bin_location: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[int] = mapped_column(Integer)
    priority: Mapped[str] = mapped_column(String(12), default="normal")
    status: Mapped[str] = mapped_column(String(16), index=True, default="open")
    assigned_worker_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    exception_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)

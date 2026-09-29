"""SQLAlchemy ORM tables. Column names follow the course data model."""
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Boolean, DateTime, Double, Integer, String
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.services.clock import utc_now

# MySQL DATETIME drops fractional seconds unless asked; keep microseconds for event ordering.
PreciseDateTime = DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")


class Base(DeclarativeBase):
    pass


class WorkerRow(Base):
    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(16))
    speed: Mapped[float] = mapped_column(Double)
    cur_x: Mapped[int] = mapped_column(Integer)
    cur_y: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="idle")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(PreciseDateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(PreciseDateTime, default=utc_now, onupdate=utc_now)


class EventRow(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(PreciseDateTime, index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    task_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    worker_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

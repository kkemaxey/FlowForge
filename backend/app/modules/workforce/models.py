"""SQLAlchemy ORM table for workers. Column names follow the course data model."""
from datetime import datetime

from sqlalchemy import Boolean, Double, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utc_now
from app.core.database import Base, PreciseDateTime


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

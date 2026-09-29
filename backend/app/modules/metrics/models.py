"""SQLAlchemy ORM table for warehouse events. Column names follow the course data model."""
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, PreciseDateTime


class EventRow(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(PreciseDateTime, index=True)
    type: Mapped[str] = mapped_column(String(32), index=True)
    task_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    worker_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    qty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

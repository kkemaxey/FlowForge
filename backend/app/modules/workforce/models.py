"""Worker table. Draft by Kendyn for the simulator and seed data; Trent to review."""
from datetime import datetime

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, Timestamp, utcnow

WORKER_KINDS = ("human", "robot")
WORKER_STATUSES = ("idle", "busy", "down")


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16))
    # Grid cells travelled per second of simulated time.
    speed: Mapped[float] = mapped_column(Float, default=1.0)
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(16), default="idle")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)

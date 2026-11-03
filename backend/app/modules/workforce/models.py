"""Workers: human pickers and robots. Base version per the database design; extend here."""
import enum
from datetime import datetime

from sqlalchemy import Boolean, Enum, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, Timestamp3, utcnow


class WorkerKind(str, enum.Enum):
    human = "human"
    robot = "robot"


class WorkerStatus(str, enum.Enum):
    idle = "idle"
    busy = "busy"
    down = "down"
    offline = "offline"


class Worker(Base):
    __tablename__ = "workers"
    __table_args__ = (Index("workers_is_active_status_index", "is_active", "status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[WorkerKind] = mapped_column(
        Enum(WorkerKind, name="worker_kind", values_callable=lambda e: [m.value for m in e])
    )
    status: Mapped[WorkerStatus] = mapped_column(
        Enum(WorkerStatus, name="worker_status", values_callable=lambda e: [m.value for m in e]),
        default=WorkerStatus.idle,
    )
    x: Mapped[int] = mapped_column(Integer)
    y: Mapped[int] = mapped_column(Integer)
    speed: Mapped[float] = mapped_column(Float, default=1.0, server_default="1")
    # Soft delete: deactivating keeps assignment history intact.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    # Bumped on every change; PATCH and DELETE compare-and-set on it (409 version_conflict).
    version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(Timestamp3, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(Timestamp3, default=utcnow, onupdate=utcnow)

"""The `workers` table from the course data model."""
from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WorkerRecord(Base):
    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    type: Mapped[str] = mapped_column(String(10), index=True)
    speed: Mapped[float] = mapped_column(Float)
    cur_x: Mapped[int] = mapped_column(Integer)
    cur_y: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), index=True, default="idle")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

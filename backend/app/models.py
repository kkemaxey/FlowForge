from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    worker_type: Mapped[str] = mapped_column("type", String(50), nullable=False)
    speed: Mapped[int] = mapped_column(Integer, nullable=False)
    cur_x: Mapped[int] = mapped_column(Integer, nullable=False)
    cur_y: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="idle")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    @property
    def type(self) -> str:
        return self.worker_type

    @type.setter
    def type(self, value: str) -> None:
        self.worker_type = value

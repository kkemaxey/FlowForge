"""App users mapped to Firebase accounts. Draft by Kendyn for the seed script; Brock to review."""
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, Timestamp, utcnow

USER_ROLES = ("supervisor", "service")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    role: Mapped[str] = mapped_column(String(32), default="supervisor")
    created_at: Mapped[datetime] = mapped_column(Timestamp, default=utcnow)

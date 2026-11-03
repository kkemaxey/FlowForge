"""App users. Firebase proves identity; this table maps a Firebase UID to an app role.
Base version per the database design; extend here.
"""
import enum
from datetime import datetime

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, Timestamp3, utcnow


class UserRole(str, enum.Enum):
    supervisor = "supervisor"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True)
    email: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        default=UserRole.supervisor,
    )
    created_at: Mapped[datetime] = mapped_column(Timestamp3, default=utcnow)

"""Database tables: users and login events."""
from sqlalchemy import Column, Integer, String, DateTime, func

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(128), unique=True, nullable=False, index=True)   # Firebase UID
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(32), nullable=False, default="worker")
    created_at = Column(DateTime, server_default=func.now())


class LoginEvent(Base):
    __tablename__ = "login_events"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(128), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

"""Database engine construction, the declarative Base, and the per-request session.

The URL always comes from configuration, never from code."""
from typing import Any, Dict, Iterator

from fastapi import Request
from sqlalchemy import DateTime, create_engine
from sqlalchemy.dialects import mysql
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session
from sqlalchemy.pool import StaticPool

# MySQL DATETIME drops fractional seconds unless asked; keep microseconds for event ordering.
PreciseDateTime = DateTime().with_variant(mysql.DATETIME(fsp=6), "mysql")


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str) -> Engine:
    options: Dict[str, Any] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if database_url in ("sqlite://", "sqlite:///:memory:"):
            # One shared connection so every session sees the same in-memory database.
            options["poolclass"] = StaticPool
    return create_engine(database_url, **options)


def get_session(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()

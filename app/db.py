"""Database engine construction. The URL always comes from configuration, never from code."""
from typing import Any, Dict

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool


def build_engine(database_url: str) -> Engine:
    options: Dict[str, Any] = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
        if database_url in ("sqlite://", "sqlite:///:memory:"):
            # One shared connection so every session sees the same in-memory database.
            options["poolclass"] = StaticPool
    return create_engine(database_url, **options)

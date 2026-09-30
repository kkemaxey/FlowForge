"""Test setup: force a throwaway SQLite DB and dev mode before app import,
and give every test a fresh, empty schema so tests can't contaminate each other."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_flowforge.db")
os.environ.setdefault("DEV_MODE", "true")
os.environ.setdefault("SUPERVISOR_EMAILS", "maria@flowforge.example")

import pytest


@pytest.fixture(autouse=True)
def fresh_db():
    """Drop and recreate all tables around each test for isolation."""
    from app.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

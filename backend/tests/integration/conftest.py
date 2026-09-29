"""Spins up the real app against a throwaway database for each test.

By default the database is a temporary SQLite file. Set TEST_DATABASE_URL to run the
same tests against MySQL; the database name must contain 'test' because every table
is dropped afterwards.
"""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.core.database import Base
from app.main import create_app


def resolve_test_database_url(tmp_path) -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        return f"sqlite:///{tmp_path / 'flowforge_test.db'}"
    database_name = make_url(url).database or ""
    if "test" not in database_name.lower():
        pytest.exit(f"Refusing to run: TEST_DATABASE_URL points at '{database_name}', "
                    "which does not look like a test database.", returncode=2)
    return url


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(database_url=resolve_test_database_url(tmp_path),
                              log_level="INFO"))
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(app.state.database.engine)
    app.state.database.engine.dispose()

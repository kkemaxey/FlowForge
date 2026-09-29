import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import Base
from app.main import create_app
from tests.integration.database_guard import is_disposable_database


@pytest.fixture
def app():
    database_url = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    if not is_disposable_database(database_url):
        pytest.exit(
            "Refusing to run integration tests: TEST_DATABASE_URL must be in-memory SQLite or name a "
            "database containing 'test', because the tests drop every table when they finish.",
            returncode=2,
        )
    application = create_app(Settings(database_url=database_url))
    yield application
    Base.metadata.drop_all(application.state.engine)
    application.state.engine.dispose()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client

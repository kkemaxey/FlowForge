import os

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import Base
from app.main import create_app


@pytest.fixture
def app():
    database_url = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    application = create_app(Settings(database_url=database_url))
    yield application
    Base.metadata.drop_all(application.state.engine)
    application.state.engine.dispose()


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.server import app

TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=TEST_ENGINE, class_=Session, expire_on_commit=False)


@pytest.fixture(autouse=True)
def isolated_database():
    Base.metadata.create_all(bind=TEST_ENGINE)

    def override_get_db():
        with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=TEST_ENGINE)


client = TestClient(app)


def test_workers_endpoints_read_and_write_workers():
    create_response = client.post(
        "/api/workers",
        json={
            "name": "Packing Bot",
            "type": "robot",
            "speed": 5,
            "cur_x": 1,
            "cur_y": 4,
        },
    )

    assert create_response.status_code == 201
    assert create_response.json()["name"] == "Packing Bot"

    response = client.get("/api/workers")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) == 1

    first = payload[0]
    required_keys = {"id", "name", "type", "speed", "cur_x", "cur_y", "status", "enabled"}
    assert required_keys.issubset(first.keys())

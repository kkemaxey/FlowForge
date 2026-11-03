"""Auth module: provision on /auth/session, read on /auth/me, and the error shape.

Follows the repo test conventions: the `db` fixture needs MySQL and is skipped in
CI without it (run inside Docker with `docker compose exec backend pytest`).
get_current_user is overridden so no live Firebase token is needed.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.security import get_current_user
from app.main import app
from app.modules.auth.models import User

SUPERVISOR_TOKEN = {"uid": "test-supervisor-uid", "email": "supervisor@flowforge.local"}


@pytest.fixture
def as_supervisor():
    app.dependency_overrides[get_current_user] = lambda: SUPERVISOR_TOKEN
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_session_provisions_user_then_me_reads(client: TestClient, db, as_supervisor):
    created = client.post("/auth/session")
    assert created.status_code == 200
    body = created.json()
    assert body["firebase_uid"] == SUPERVISOR_TOKEN["uid"]
    assert body["role"] == "supervisor"
    assert body["is_supervisor"] is True

    db.rollback()
    assert db.query(User).filter_by(firebase_uid=SUPERVISOR_TOKEN["uid"]).count() == 1

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == SUPERVISOR_TOKEN["email"]


def test_me_before_session_is_404(client: TestClient, db, as_supervisor):
    resp = client.get("/auth/me")
    assert resp.status_code == 404
    assert resp.json()["code"] == "not_provisioned"


def test_missing_token_is_401(client: TestClient, db):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    assert resp.json()["code"] == "unauthorized"

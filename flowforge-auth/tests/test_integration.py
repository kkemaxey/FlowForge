"""Integration test — runs against a real API endpoint through the full stack
(routing, DB read/write), with only the Firebase identity dependency overridden
so we don't need a live token."""
from fastapi.testclient import TestClient

from app.auth import get_current_identity
from app.main import app


def fake_supervisor_identity():
    return {"uid": "test-uid", "email": "maria@flowforge.example"}


app.dependency_overrides[get_current_identity] = fake_supervisor_identity
client = TestClient(app)


def test_login_then_me_end_to_end():
    # POST /auth/login writes the user + a login event, returns supervisor flag.
    login = client.post("/auth/login")
    assert login.status_code == 200
    body = login.json()
    assert body["message"] == "Login recorded"
    assert body["user"]["is_supervisor"] is True

    # GET /auth/me reads the same user back from the database.
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "maria@flowforge.example"
    assert me.json()["role"] == "supervisor"


def test_missing_token_is_rejected():
    # With no override, the real dependency should 401 on a missing token.
    app.dependency_overrides.pop(get_current_identity, None)
    try:
        resp = client.get("/auth/me")
        assert resp.status_code == 401
    finally:
        app.dependency_overrides[get_current_identity] = fake_supervisor_identity

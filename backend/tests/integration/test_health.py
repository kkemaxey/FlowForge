import logging

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.version import read_version


class UnreachableEngine:
    def connect(self):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_health_reports_version_and_database(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": read_version(), "db": "ok"}


def test_health_returns_503_when_database_is_unreachable(app, client):
    real_engine = app.state.engine
    app.state.engine = UnreachableEngine()
    try:
        response = client.get("/health")
    finally:
        app.state.engine = real_engine

    assert response.status_code == 503
    assert response.json()["db"] == "unreachable"


def test_every_response_carries_a_request_id(client):
    generated = client.get("/health")
    echoed = client.get("/health", headers={"X-Request-ID": "demo-123"})

    assert generated.headers["X-Request-ID"]
    assert echoed.headers["X-Request-ID"] == "demo-123"


def test_requests_are_logged_on_arrival_and_completion(client, caplog):
    caplog.set_level(logging.INFO, logger="flowforge.requests")

    client.get("/health", headers={"X-Request-ID": "log-check"})

    messages = [record.getMessage() for record in caplog.records if record.name == "flowforge.requests"]
    assert any("request received" in m and "path=/health" in m and "request_id=log-check" in m
               for m in messages)
    assert any("request completed" in m and "status=200" in m and "duration_ms=" in m
               for m in messages)


def test_unknown_route_uses_error_envelope(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"error": {"code": "not_found", "message": "Not Found"}}


def test_unhandled_error_returns_generic_500_envelope(app):
    def explode():
        raise RuntimeError("secret internal detail")

    app.add_api_route("/boom", explode)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/boom")

    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "internal_error", "message": "An unexpected error occurred"}
    }

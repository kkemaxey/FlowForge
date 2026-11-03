"""Framework-level errors use the same {"detail", "code"} shape as the API's own errors."""
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import create_app


def test_unknown_route_is_404_not_found(client):
    response = client.get("/api/v1/nope")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found", "code": "not_found"}


def test_wrong_method_is_405_and_keeps_allow_header(client):
    response = client.delete("/api/v1/assignments/run")

    assert response.status_code == 405
    assert response.json() == {"detail": "Method Not Allowed", "code": "method_not_allowed"}
    assert response.headers["allow"] == "POST"


def test_http_exception_keeps_its_status_and_headers():
    app = create_app()

    @app.get("/boom-401")
    def unauthorized():
        raise HTTPException(401, "Missing bearer token", headers={"WWW-Authenticate": "Bearer"})

    response = TestClient(app).get("/boom-401")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token", "code": "unauthorized"}
    assert response.headers["www-authenticate"] == "Bearer"


def test_unexpected_crash_is_500_without_internals():
    app = create_app()

    @app.get("/boom-500")
    def crash():
        raise RuntimeError("secret database password in this message")

    # raise_server_exceptions=False: return the 500 response instead of re-raising in the test.
    response = TestClient(app, raise_server_exceptions=False).get("/boom-500")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error", "code": "internal_error"}
    assert "secret" not in response.text

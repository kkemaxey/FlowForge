"""Every request is logged on arrival and completion with a request id, which is echoed back."""
import logging

import pytest

LOGGER = "uvicorn.error.requests"


@pytest.fixture(autouse=True)
def logger_enabled():
    """The migrated_db fixture runs Alembic, whose fileConfig() disables every existing logger in the
    test process. Re-enable ours for these tests; the real server never runs Alembic in-process."""
    logger = logging.getLogger(LOGGER)
    was_disabled = logger.disabled
    logger.disabled = False
    yield
    logger.disabled = was_disabled


def messages(caplog):
    return [record.getMessage() for record in caplog.records if record.name == LOGGER]


def test_request_is_logged_on_arrival_and_completion(client, caplog):
    caplog.set_level(logging.INFO, logger=LOGGER)

    client.get("/health", headers={"X-Request-ID": "trace-123"})

    logged = messages(caplog)
    assert any("request received" in m and "path=/health" in m and "request_id=trace-123" in m for m in logged)
    assert any("request completed" in m and "status=200" in m and "duration_ms=" in m for m in logged)


def test_request_id_is_echoed_or_generated(client):
    echoed = client.get("/health", headers={"X-Request-ID": "trace-456"})
    generated = client.get("/health")

    assert echoed.headers["X-Request-ID"] == "trace-456"
    assert len(generated.headers["X-Request-ID"]) == 12


def test_error_responses_are_logged_with_their_status(client, caplog):
    caplog.set_level(logging.INFO, logger=LOGGER)

    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert any("request completed" in m and "status=404" in m for m in messages(caplog))

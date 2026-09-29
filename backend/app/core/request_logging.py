"""Logs every request when it arrives and when it completes, tagged with a request id."""
import logging
import time
import uuid

from fastapi import FastAPI, Request

logger = logging.getLogger("flowforge.requests")

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(level: str) -> None:
    logging.basicConfig(level=level, format=LOG_FORMAT)
    logging.getLogger("flowforge").setLevel(level)


def register_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_request(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        path = request.url.path
        logger.info("request received method=%s path=%s request_id=%s",
                    request.method, path, request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.exception("request failed method=%s path=%s duration_ms=%.1f request_id=%s",
                             request.method, path, duration_ms, request_id)
            raise
        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        logger.info("request completed method=%s path=%s status=%d duration_ms=%.1f request_id=%s",
                    request.method, path, response.status_code, duration_ms, request_id)
        return response

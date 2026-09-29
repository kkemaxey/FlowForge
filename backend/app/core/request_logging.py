"""Request logging: one line when a request arrives, one when its response leaves."""
import logging
import time
import uuid

from fastapi import FastAPI, Request

request_logger = logging.getLogger("flowforge.requests")


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    logging.getLogger("flowforge").setLevel(level)


def register_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_each_request(request: Request, call_next):
        # Reuse the caller's id when given so a request can be traced across services.
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        client_host = request.client.host if request.client else "unknown"
        request_logger.info("incoming %s %s from=%s request_id=%s",
                            request.method, request.url.path, client_host, request_id)

        start_time = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        response.headers["X-Request-ID"] = request_id
        request_logger.info("finished %s %s status=%d elapsed_ms=%.1f request_id=%s",
                            request.method, request.url.path, response.status_code,
                            elapsed_ms, request_id)
        return response

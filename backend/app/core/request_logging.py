"""One log line when each request arrives and one when it finishes, tied together by a request id.

The id comes from the caller's X-Request-ID header when present, otherwise it is generated, and it
is echoed back on the response so a frontend error can be matched to the server log. Bodies and
query strings are never logged.
"""
import logging
import time
import uuid

from fastapi import FastAPI, Request

logger = logging.getLogger("uvicorn.error").getChild("requests")


def register_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def log_request(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        logger.info("request received method=%s path=%s request_id=%s", request.method, request.url.path, request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "request failed method=%s path=%s duration_ms=%.1f request_id=%s",
                request.method, request.url.path, (time.perf_counter() - started) * 1000, request_id,
            )
            raise
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed method=%s path=%s status=%d duration_ms=%.1f request_id=%s",
            request.method, request.url.path, response.status_code, (time.perf_counter() - started) * 1000, request_id,
        )
        return response

"""API errors in the shape every endpoint returns: {"detail": "<message>", "code": "<machine_code>"}.

409 always means a state conflict (stale version, task already moved on, or a unique key
rejecting a race). Raise ApiError from services; the handlers below format the response.
"""
import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("uvicorn.error")

# Codes for errors raised by FastAPI/Starlette itself (unknown route, wrong method) or by an
# HTTPException elsewhere (e.g. auth's 401). Anything unlisted gets "http_error".
HTTP_ERROR_CODES = {
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
}


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.code = code
        self.detail = detail


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail, "code": exc.code})

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Same shape as other errors; the field-level list stays under "errors" for debugging.
        errors = exc.errors()
        first = errors[0] if errors else {}
        where = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
        detail = f"{where}: {first.get('msg', 'invalid request')}" if where else first.get("msg", "invalid request")
        return JSONResponse(
            status_code=422,
            content={"detail": detail, "code": "validation_error", "errors": jsonable_encoder(errors)},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Keep headers such as Allow (405) and WWW-Authenticate (401).
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail), "code": HTTP_ERROR_CODES.get(exc.status_code, "http_error")},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Never leak internals to the client; the full traceback goes to the server log.
        logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
        return JSONResponse(status_code=500, content={"detail": "Internal server error", "code": "internal_error"})

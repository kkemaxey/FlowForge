"""Maps every failure to the single error envelope: {"error": {"code", "message"}}."""
import logging
from typing import Dict, Tuple, Type

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import ConflictError, DomainError, NotFoundError, RuleViolationError

logger = logging.getLogger("flowforge.errors")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail

DOMAIN_ERROR_STATUS: Tuple[Tuple[Type[DomainError], int], ...] = (
    (NotFoundError, 404),
    (ConflictError, 409),
    (RuleViolationError, 422),
)

HTTP_ERROR_CODES: Dict[int, str] = {404: "not_found", 405: "method_not_allowed"}


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def _describe_validation_error(error: dict) -> str:
    location = ".".join(str(part) for part in error["loc"] if part != "body")
    return f"{location}: {error['msg']}" if location else error["msg"]


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, exc: DomainError):
        status_code = next(
            (status for error_type, status in DOMAIN_ERROR_STATUS if isinstance(exc, error_type)),
            400,
        )
        return JSONResponse(status_code=status_code, content=error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        message = "; ".join(_describe_validation_error(error) for error in exc.errors())
        return JSONResponse(status_code=422, content=error_body("validation_error", message))

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        code = HTTP_ERROR_CODES.get(exc.status_code, "http_error")
        return JSONResponse(status_code=exc.status_code, content=error_body(code, str(exc.detail)))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500,
                            content=error_body("internal_error", "An unexpected error occurred"))

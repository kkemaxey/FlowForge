"""Domain exceptions and the JSON error envelope returned to clients."""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("flowforge.errors")


class DomainError(Exception):
    """Base class for errors the business layer raises on purpose."""

    status_code = status.HTTP_400_BAD_REQUEST
    code = "bad_request"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class InvalidTransitionError(DomainError):
    status_code = status.HTTP_409_CONFLICT
    code = "invalid_transition"


class ValidationFailedError(DomainError):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    code = "validation_failed"


def error_body(code: str, message: str, details: list | None = None) -> dict:
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return body


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(request: Request, error: DomainError):
        logger.warning("domain error code=%s path=%s message=%s",
                       error.code, request.url.path, error.message)
        return JSONResponse(status_code=error.status_code,
                            content=error_body(error.code, error.message))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(request: Request, error: RequestValidationError):
        details = [
            {"field": ".".join(str(part) for part in issue["loc"]), "message": issue["msg"]}
            for issue in error.errors()
        ]
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                            content=error_body("validation_failed",
                                               "Request body or parameters are invalid.",
                                               details))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, error: Exception):
        logger.exception("unhandled error path=%s", request.url.path)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content=error_body("internal_error", "Something went wrong."))

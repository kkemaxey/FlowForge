import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("flowforge.health")

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Service and database health",
    description="Returns the running version and whether the database answers a trivial query.",
    responses={503: {"description": "Database unreachable"}},
)
def health(request: Request):
    state = request.app.state
    try:
        with state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        return JSONResponse(status_code=503,
                            content={"status": "degraded", "version": state.version, "db": "unreachable"})
    return {"status": "ok", "version": state.version, "db": "ok"}

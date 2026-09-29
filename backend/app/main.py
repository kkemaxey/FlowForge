"""FlowForge API entry point.

Run from backend/:  uvicorn app.main:create_app --factory
"""
from fastapi import FastAPI, Response, status

from app.core.config import Settings, load_settings
from app.core.database import Database
from app.core.errors import register_error_handlers
from app.core.request_logging import configure_logging, register_request_logging
from app.core.version import app_version
from app.modules.workforce.router import router as workforce_router


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="FlowForge API",
        version=app_version(),
        description="Workforce API for the FlowForge control tower: add workers and "
                    "list who is on the floor.",
    )
    database = Database(settings.database_url)
    database.create_tables()
    app.state.database = database

    register_request_logging(app)
    register_error_handlers(app)
    app.include_router(workforce_router)

    @app.get("/health", tags=["health"], summary="Service and database health")
    def health(response: Response):
        database_ok = database.is_reachable()
        if not database_ok:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "ok" if database_ok else "degraded",
                "version": app_version(),
                "database": "connected" if database_ok else "unreachable"}

    return app


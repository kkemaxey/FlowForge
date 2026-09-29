"""FlowForge API. Run with: uvicorn app.main:create_app --factory --reload"""
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from app.api_errors import register_error_handlers
from app.config import Settings, load_settings
from app.db import build_engine
from app.models import Base
from app.request_logging import configure_logging, register_request_logging
from app.routers import health, workers
from app.version import read_version

logger = logging.getLogger("flowforge")


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)
    engine = build_engine(settings.database_url)
    version = read_version()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        Base.metadata.create_all(engine)
        logger.info("FlowForge API %s started", version)
        yield
        engine.dispose()

    app = FastAPI(
        title="FlowForge API",
        version=version,
        description="Workforce management and throughput metrics for the FlowForge warehouse control tower.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    app.state.version = version

    register_request_logging(app)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(workers.router)
    return app

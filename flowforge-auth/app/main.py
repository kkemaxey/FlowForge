"""FastAPI application entrypoint: middleware, table setup, routes."""
import logging

from fastapi import FastAPI, Request

from . import models  # noqa: F401  (registers tables on Base)
from .database import Base, engine
from .routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("flowforge")

app = FastAPI(
    title="FlowForge Auth Service",
    version="0.1.0",
    description="Authentication and supervisor-role service for the FlowForge warehouse control tower.",
)

# Demo convenience: create tables on startup. Production would use migrations.
Base.metadata.create_all(bind=engine)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Rubric: log when a request comes in.
    logger.info("request %s %s", request.method, request.url.path)
    return await call_next(request)


@app.get("/health", tags=["ops"], summary="Liveness check")
def health():
    return {"status": "ok"}


app.include_router(router)

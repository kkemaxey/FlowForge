"""FastAPI entry point. Each module owns its router; add new modules to ROUTERS only."""
import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import register_error_handlers
from app.modules.assignment.loop import assigner_loop
from app.modules.assignment.router import router as assignment_router
from app.modules.auth.router import router as auth_router
from app.modules.events.router import router as events_router
from app.modules.generator.router import router as generator_router
from app.modules.generator.service import generator
from app.modules.orders.router import router as orders_router
from app.modules.simulation.router import router as simulation_router
from app.modules.tasks.router import router as tasks_router
from app.modules.workforce.router import router as workforce_router

ROUTERS = [
    auth_router,
    orders_router,
    tasks_router,
    assignment_router,
    simulation_router,
    workforce_router,
    events_router,
    generator_router,
]


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Background work that lives as long as the app: the assigner loop (when enabled) and the
    order generator (when started through the API)."""
    stop = asyncio.Event()
    loop_task = None
    if settings.assigner_loop_enabled:
        loop_task = asyncio.create_task(assigner_loop(settings.assigner_interval_seconds, stop))
    yield
    await generator.stop()  # records the run's end time on shutdown or reload
    stop.set()
    if loop_task is not None:
        await loop_task


def create_app() -> FastAPI:
    app = FastAPI(title="FlowForge API", lifespan=lifespan)
    register_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for router in ROUTERS:
        app.include_router(router)

    return app


app = create_app()

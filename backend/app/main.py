"""FastAPI entry point. Each module owns its router; add new modules to ROUTERS only."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.modules.assignment.router import router as assignment_router
from app.modules.auth.router import router as auth_router
from app.modules.events.router import router as events_router
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
]


def create_app() -> FastAPI:
    app = FastAPI(title="FlowForge API")

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

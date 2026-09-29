"""Wires a database session and repositories into each request's service."""
from typing import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.repositories.event_repo import SqlEventRepository
from app.repositories.worker_repo import SqlWorkerRepository
from app.services.metrics import MetricsService
from app.services.workforce import GridBounds, WorkforceService


def get_session(request: Request) -> Iterator[Session]:
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def get_workforce_service(request: Request, session: Session = Depends(get_session)) -> WorkforceService:
    settings = request.app.state.settings
    grid = GridBounds(width=settings.grid_width, height=settings.grid_height)
    return WorkforceService(SqlWorkerRepository(session), grid)


def get_metrics_service(session: Session = Depends(get_session)) -> MetricsService:
    return MetricsService(SqlEventRepository(session), SqlWorkerRepository(session))

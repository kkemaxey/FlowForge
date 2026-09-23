from __future__ import annotations

from fastapi import Depends, FastAPI, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .services import create_worker, list_workers as fetch_workers

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FlowForge API")


class WorkerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=50)
    speed: int = Field(ge=0)
    cur_x: int
    cur_y: int
    status: str = Field(default="idle", min_length=1, max_length=50)
    enabled: bool = True


@app.get("/")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/workers")
def list_workers(session: Session = Depends(get_db)) -> list[dict[str, object]]:
    return fetch_workers(session)


@app.post("/api/workers", status_code=status.HTTP_201_CREATED)
def add_worker(
    worker: WorkerCreate,
    session: Session = Depends(get_db),
) -> dict[str, object]:
    return create_worker(session, worker.model_dump() | {"worker_type": worker.type})

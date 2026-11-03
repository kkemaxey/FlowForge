"""Request and response bodies for /api/v1/workers."""
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.schemas import UtcDatetime
from app.modules.workforce.models import Worker, WorkerKind, WorkerStatus

Name = Annotated[str, Field(min_length=1, max_length=64)]
Coordinate = Annotated[int, Field(ge=0)]
Speed = Annotated[float, Field(gt=0, le=99.99)]


class WorkerCreate(BaseModel):
    """status, is_active and version are server-owned: sending them is a 422."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Name
    kind: WorkerKind
    x: Coordinate
    y: Coordinate
    speed: Speed = 1.0


class WorkerUpdate(BaseModel):
    """Partial edit guarded by expected_version. status belongs to the assigner and simulator."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    expected_version: Annotated[int, Field(ge=0)]
    name: Name | None = None
    kind: WorkerKind | None = None
    x: Coordinate | None = None
    y: Coordinate | None = None
    speed: Speed | None = None

    @model_validator(mode="after")
    def no_explicit_nulls(self) -> Self:
        # Omit a field to leave it alone; null would mean "clear it", and none of these can be empty.
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class WorkerOut(BaseModel):
    worker_id: int
    name: str
    kind: WorkerKind
    status: WorkerStatus
    x: int
    y: int
    speed: float
    is_active: bool
    version: int
    created_at: UtcDatetime
    updated_at: UtcDatetime

    @classmethod
    def of(cls, worker: Worker) -> "WorkerOut":
        return cls(
            worker_id=worker.id,
            name=worker.name,
            kind=worker.kind,
            status=worker.status,
            x=worker.x,
            y=worker.y,
            speed=worker.speed,
            is_active=worker.is_active,
            version=worker.version,
            created_at=worker.created_at,
            updated_at=worker.updated_at,
        )


class WorkerListOut(BaseModel):
    items: list[WorkerOut]
    count: int  # number of items in this response

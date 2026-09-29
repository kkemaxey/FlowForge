"""Request and response shapes for workers."""
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

# The warehouse floor from the course map seed is a 20 x 12 grid.
GRID_WIDTH = 20
GRID_HEIGHT = 12


class WorkerType(StrEnum):
    HUMAN = "human"
    ROBOT = "robot"


class WorkerStatus(StrEnum):
    IDLE = "idle"
    BUSY = "busy"


class WorkerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60, examples=["Maria Lopez"])
    type: WorkerType = Field(examples=["human"])
    speed: float = Field(gt=0, examples=[1.2], description="Travel speed in grid cells per second.")
    cur_x: int = Field(default=0, ge=0, lt=GRID_WIDTH, description="Column on the floor grid.")
    cur_y: int = Field(default=0, ge=0, lt=GRID_HEIGHT, description="Row on the floor grid.")
    status: WorkerStatus = WorkerStatus.IDLE
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if not value:
            raise ValueError("name must not be blank")
        return value


class WorkerView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: WorkerType
    speed: float
    cur_x: int
    cur_y: int
    status: WorkerStatus
    enabled: bool

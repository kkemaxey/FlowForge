"""Response shapes for warehouse data, shared by modules that show where a task is."""
from pydantic import BaseModel

from app.modules.warehouse.models import Location, LocationKind


class LocationOut(BaseModel):
    location_id: int
    x: int
    y: int
    kind: LocationKind
    zone: str | None
    aisle: str | None

    @classmethod
    def of(cls, location: Location) -> "LocationOut":
        return cls(
            location_id=location.id,
            x=location.x,
            y=location.y,
            kind=location.kind,
            zone=location.zone,
            aisle=location.aisle,
        )


class LocationListOut(BaseModel):
    items: list[LocationOut]
    count: int  # number of items in this response

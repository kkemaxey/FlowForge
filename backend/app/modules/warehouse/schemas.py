"""Response shapes for warehouse data, shared by modules that show where a task is."""
from pydantic import BaseModel

from app.modules.warehouse.models import Location


class LocationOut(BaseModel):
    location_id: int
    x: int
    y: int
    zone: str | None
    aisle: str | None

    @classmethod
    def of(cls, location: Location) -> "LocationOut":
        return cls(location_id=location.id, x=location.x, y=location.y, zone=location.zone, aisle=location.aisle)

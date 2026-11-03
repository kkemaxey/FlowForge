"""Reads of the static warehouse data."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.warehouse.models import Location
from app.modules.warehouse.schemas import LocationListOut, LocationOut


def list_locations(session: Session) -> LocationListOut:
    """Every location in the warehouse, row by row (y, then x)."""
    locations = session.scalars(select(Location).order_by(Location.y, Location.x)).all()
    items = [LocationOut.of(location) for location in locations]
    return LocationListOut(items=items, count=len(items))

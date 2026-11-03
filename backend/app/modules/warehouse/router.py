from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.warehouse import service
from app.modules.warehouse.schemas import LocationListOut

router = APIRouter(prefix="/api/v1/locations", tags=["warehouse"])


@router.get("", response_model=LocationListOut)
def list_locations(db: Session = Depends(get_db)) -> LocationListOut:
    """Every location, for drawing the warehouse grid. There is one warehouse, so no limit."""
    return service.list_locations(db)

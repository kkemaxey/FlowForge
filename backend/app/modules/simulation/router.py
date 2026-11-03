from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.simulation import service
from app.modules.simulation.schemas import PickCreate, PickOut

router = APIRouter(prefix="/api/v1", tags=["simulation"])


@router.post("/tasks/{task_id}/pick", response_model=PickOut)
def pick_task(task_id: int, payload: PickCreate, db: Session = Depends(get_db)) -> PickOut:
    """A worker finished picking: remove the stock, free the worker, and complete the order if done."""
    return service.pick_task(db, task_id, payload.assignment_id)

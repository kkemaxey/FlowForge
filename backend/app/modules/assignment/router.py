from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.assignment import service
from app.modules.assignment.schemas import RunRequest, RunResult

router = APIRouter(prefix="/api/v1/assignments", tags=["assignments"])


@router.post("/run", response_model=RunResult)
def run_assigner(payload: RunRequest | None = None, db: Session = Depends(get_db)) -> RunResult:
    """Run one assigner pass now (the background loop also runs one every few seconds)."""
    payload = payload or RunRequest()
    return service.run_pass(db, payload.algorithm, payload.run_id)

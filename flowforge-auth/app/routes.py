"""The two API endpoints (thin controllers).

They delegate the decision logic to services.py and the persistence to crud.py,
so the handlers themselves stay small.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from . import crud, services
from .auth import get_current_identity
from .config import get_settings
from .database import get_db
from .schemas import LoginResponse, UserProfile

logger = logging.getLogger("flowforge.auth")
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate a Firebase user, assign their role, and record the login",
)
def login(
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    role = services.assign_role(identity["email"], get_settings().supervisor_emails)
    user = crud.upsert_user(db, identity["uid"], identity["email"], role)  # WRITE
    crud.record_login(db, user.uid, user.email)                           # WRITE
    logger.info("login recorded uid=%s role=%s", user.uid, user.role)
    return {"message": "Login recorded", "user": services.build_profile(user.uid, user.email, user.role)}


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Return the current authenticated user and whether they are a supervisor",
)
def me(
    identity: dict = Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    user = crud.get_user_by_uid(db, identity["uid"])  # READ
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found; call POST /auth/login first",
        )
    return services.build_profile(user.uid, user.email, user.role)

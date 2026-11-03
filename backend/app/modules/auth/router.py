"""Auth endpoints: provision/sync the app user, and read the current user."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.auth import service
from app.modules.auth.models import User
from app.modules.auth.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/session",
    response_model=UserOut,
    summary="Provision or sync the app user from a Firebase token and record the login",
)
def create_session(
    token: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> User:
    """Called right after Firebase sign-in. Writes the user row and a login event."""
    return service.provision_user(session, token)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Return the current authenticated user and supervisor status",
)
def read_me(user: User = Depends(service.current_app_user)) -> User:
    return user

"""Auth business logic.

Firebase proves identity (core.security verifies the token); this module maps the
verified UID to an app user and provides the supervisor gate other modules use to
protect writes.
"""
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ApiError
from app.core.security import get_current_user
from app.modules.auth.models import User, UserRole
from app.modules.events.models import Event


def get_user_by_uid(session: Session, firebase_uid: str) -> User | None:
    return session.scalar(select(User).where(User.firebase_uid == firebase_uid))


def provision_user(session: Session, token: dict) -> User:
    """Upsert the app user for a verified Firebase token and log the login.

    First login creates the row (default role supervisor); later logins keep the
    email in sync. A `user_login` row is appended to the events log either way.
    """
    uid = token["uid"]
    email = token.get("email")

    user = get_user_by_uid(session, uid)
    if user is None:
        user = User(firebase_uid=uid, email=email, role=UserRole.supervisor)
        session.add(user)
    elif email and user.email != email:
        user.email = email

    session.add(Event(event_type="user_login", payload={"firebase_uid": uid, "email": email}))
    session.commit()
    session.refresh(user)
    return user


def current_app_user(
    token: dict = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> User:
    """Dependency: the User row for the caller, or 404 if not yet provisioned."""
    user = get_user_by_uid(session, token["uid"])
    if user is None:
        raise ApiError(404, "not_provisioned", "User not provisioned; POST /auth/session first")
    return user


def require_supervisor(user: User = Depends(current_app_user)) -> User:
    """Dependency other modules add to gate supervisor-only writes.

    users.role currently has a single value (supervisor); the check is explicit so
    adding roles later only means extending the comparison.
    """
    if user.role != UserRole.supervisor:
        raise ApiError(403, "forbidden", "Supervisor role required")
    return user

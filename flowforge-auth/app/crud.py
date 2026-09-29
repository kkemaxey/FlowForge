"""Database read/write helpers.

All access goes through the SQLAlchemy ORM, which parameterizes every query —
so there is no string-built SQL and no SQL-injection surface.
"""
from sqlalchemy.orm import Session

from . import models


def get_user_by_uid(db: Session, uid: str):
    """READ: fetch a single user by Firebase UID."""
    return db.query(models.User).filter(models.User.uid == uid).first()


def upsert_user(db: Session, uid: str, email: str, role: str) -> "models.User":
    """WRITE: insert the user, or update email/role if they already exist."""
    user = get_user_by_uid(db, uid)
    if user is None:
        user = models.User(uid=uid, email=email, role=role)
        db.add(user)
    else:
        user.email = email
        user.role = role
    db.commit()
    db.refresh(user)
    return user


def record_login(db: Session, uid: str, email: str) -> "models.LoginEvent":
    """WRITE: append a login event row."""
    event = models.LoginEvent(uid=uid, email=email)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event

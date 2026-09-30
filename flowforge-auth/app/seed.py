"""Create the database schema and populate it with sample data.

Run once before a demo:  python -m app.seed

Idempotent: re-running updates the existing users instead of duplicating them,
and only inserts login events if the table is empty.
"""
import logging

from . import crud, models
from .database import Base, SessionLocal, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flowforge.seed")

# Sample users. The two dev-* UIDs line up with the dev-mode tokens in auth.py,
# so GET /auth/me works against seeded data with no login step.
SAMPLE_USERS = [
    {"uid": "dev-supervisor-uid", "email": "maria@flowforge.example", "role": "supervisor"},
    {"uid": "dev-worker-uid", "email": "sam@flowforge.example", "role": "worker"},
    {"uid": "u-jordan", "email": "jordan@flowforge.example", "role": "worker"},
    {"uid": "u-alex", "email": "alex@flowforge.example", "role": "supervisor"},
]

SAMPLE_LOGINS = [
    {"uid": "dev-supervisor-uid", "email": "maria@flowforge.example"},
    {"uid": "dev-worker-uid", "email": "sam@flowforge.example"},
    {"uid": "u-jordan", "email": "jordan@flowforge.example"},
]


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for u in SAMPLE_USERS:
            crud.upsert_user(db, u["uid"], u["email"], u["role"])
        if db.query(models.LoginEvent).count() == 0:
            for e in SAMPLE_LOGINS:
                crud.record_login(db, e["uid"], e["email"])

        users = db.query(models.User).all()
        event_count = db.query(models.LoginEvent).count()
        print(f"\nSeeded {len(users)} users and {event_count} login events:")
        for u in users:
            print(f"  - {u.email:34} role={u.role}")
        print()
    finally:
        db.close()


if __name__ == "__main__":
    seed()

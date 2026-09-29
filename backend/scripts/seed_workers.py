"""Inserts demo workers when the workers table is empty.

Usage: python -m scripts.seed_workers
   or: docker compose exec api python -m scripts.seed_workers
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import load_settings
from app.core.database import Base, build_engine
from app.modules.workforce.models import WorkerRow

DEMO_WORKERS = [
    dict(name="Picker Ana", type="human", speed=1.0, cur_x=0, cur_y=6, status="idle", enabled=True),
    dict(name="Picker Ben", type="human", speed=1.2, cur_x=3, cur_y=2, status="busy", enabled=True),
    dict(name="Robot R1", type="robot", speed=2.5, cur_x=15, cur_y=9, status="idle", enabled=True),
    dict(name="Robot R2", type="robot", speed=2.5, cur_x=10, cur_y=4, status="idle", enabled=False),
]


def main() -> None:
    engine = build_engine(load_settings().database_url)
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        existing = session.scalar(select(func.count()).select_from(WorkerRow))
        if existing:
            print(f"workers table already has {existing} rows; skipping seed")
        else:
            session.add_all(WorkerRow(**worker) for worker in DEMO_WORKERS)
            session.commit()
            print(f"Seeded {len(DEMO_WORKERS)} workers (Picker Ben is busy, for the 409 demo)")
    engine.dispose()


if __name__ == "__main__":
    main()

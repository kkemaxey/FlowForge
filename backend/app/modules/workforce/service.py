"""Workers: create, list, edit and soft delete.

Edits and deletes are compare-and-set on workers.version, like tasks.transition(): the UPDATE
only matches if the row still has the version the client read, so two supervisors editing the
same worker can't silently overwrite each other (409 version_conflict). Both also lock the
worker row first, so the assigner can't claim the worker between our checks and our write.

Every change writes its event (worker_created, worker_updated, worker_deactivated) in the same
transaction.
"""
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import set_committed_value

from app.core.database import utcnow
from app.core.errors import ApiError
from app.modules.assignment.models import Assignment
from app.modules.events.models import Event
from app.modules.workforce.models import Worker, WorkerKind, WorkerStatus
from app.modules.workforce.schemas import WorkerCreate, WorkerListOut, WorkerOut, WorkerUpdate

# Position rule: x and y only have to be non-negative (enforced by WorkerCreate/WorkerUpdate).
# There is no upper bound yet because nothing in the schema records the warehouse's size: the
# locations table only has bins and stations, so the largest x/y in it undercounts the grid
# (the seeded 10 x 10 warehouse has no rows in walkway column 9 or open-floor row 9, where
# robots start).
#
# Planned (to agree with Kanayo, since it touches the shared core): add WAREHOUSE_WIDTH and
# WAREHOUSE_HEIGHT to core/config.py (default 10 x 10, matching seed.py), then check
# 0 <= x < width and 0 <= y < height in create_worker and in update_worker when x or y change,
# raising ApiError(422, "position_off_grid", ...). Replace the settings with the warehouse's own
# dimensions if a warehouses table is added later.


def get_worker(session: Session, worker_id: int, for_update: bool = False) -> Worker:
    """The worker, active or not, or a 404. for_update locks the row until commit/rollback."""
    worker = session.get(Worker, worker_id, with_for_update=for_update, populate_existing=for_update)
    if worker is None:
        raise ApiError(404, "worker_not_found", f"Worker {worker_id} not found")
    return worker


def list_idle_workers(session: Session) -> list[Worker]:
    """Active workers free for a task, by id."""
    return list(
        session.scalars(
            select(Worker).where(Worker.status == WorkerStatus.idle, Worker.is_active.is_(True)).order_by(Worker.id)
        )
    )


def list_workers(
    session: Session,
    status: WorkerStatus | None,
    kind: WorkerKind | None,
    include_inactive: bool,
    limit: int,
) -> WorkerListOut:
    query = select(Worker).order_by(Worker.id).limit(limit)
    if status is not None:
        query = query.where(Worker.status == status)
    if kind is not None:
        query = query.where(Worker.kind == kind)
    if not include_inactive:
        query = query.where(Worker.is_active.is_(True))
    items = [WorkerOut.of(worker) for worker in session.scalars(query)]
    return WorkerListOut(items=items, count=len(items))


def create_worker(session: Session, payload: WorkerCreate) -> Worker:
    now = utcnow()
    worker = Worker(
        name=payload.name,
        kind=payload.kind,
        x=payload.x,
        y=payload.y,
        speed=payload.speed,
        status=WorkerStatus.idle,
        is_active=True,
        version=0,
        created_at=now,
        updated_at=now,
    )
    session.add(worker)
    session.flush()
    session.add(
        Event(
            event_type="worker_created",
            worker_id=worker.id,
            payload=payload.model_dump(mode="json"),
        )
    )
    session.commit()
    return worker


def _version_conflict(worker_id: int, expected_version: int) -> ApiError:
    return ApiError(
        409, "version_conflict", f"Worker {worker_id} is no longer at version {expected_version}; reload and retry"
    )


def update_worker(session: Session, worker_id: int, payload: WorkerUpdate) -> Worker:
    """Apply the fields that differ from the row. Sending only expected_version (or only
    unchanged values) checks the version and returns the worker as is: no bump, no event."""
    try:
        worker = get_worker(session, worker_id, for_update=True)
        expected = payload.expected_version
        if worker.version != expected:
            raise _version_conflict(worker_id, expected)
        if not worker.is_active:
            raise ApiError(409, "worker_inactive", f"Worker {worker_id} is deactivated and cannot be edited")

        requested = payload.model_dump(exclude_unset=True, exclude={"expected_version"})
        changes = {field: value for field, value in requested.items() if getattr(worker, field) != value}
        if not changes:
            session.rollback()  # release the row lock
            return worker

        moving = "x" in changes or "y" in changes
        if moving and worker.status == WorkerStatus.busy:
            raise ApiError(409, "worker_busy", f"Worker {worker_id} is busy; it can be moved once it is idle")

        now = utcnow()
        result = session.execute(
            update(Worker)
            .where(Worker.id == worker_id, Worker.version == expected)
            .values(**changes, version=Worker.version + 1, updated_at=now)
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise _version_conflict(worker_id, expected)

        session.add(
            Event(
                event_type="worker_updated",
                worker_id=worker_id,
                payload={"changes": jsonable_encoder(changes)},
            )
        )
        session.commit()
    except Exception:
        session.rollback()
        raise

    # Mirror the new row on the loaded object without marking it dirty (no second UPDATE).
    for field, value in changes.items():
        set_committed_value(worker, field, value)
    set_committed_value(worker, "version", expected + 1)
    set_committed_value(worker, "updated_at", now)
    return worker


def deactivate_worker(session: Session, worker_id: int) -> None:
    """Soft delete: the row stays for assignment history. Already inactive is a no-op."""
    try:
        worker = get_worker(session, worker_id, for_update=True)
        if not worker.is_active:
            session.rollback()
            return

        open_assignment = session.scalar(
            select(Assignment.id).where(Assignment.worker_id == worker_id, Assignment.ended_at.is_(None)).limit(1)
        )
        if open_assignment is not None:
            raise ApiError(
                409,
                "worker_has_open_assignment",
                f"Worker {worker_id} has open assignment {open_assignment}; reassign or finish it first",
            )

        result = session.execute(
            update(Worker)
            .where(Worker.id == worker_id, Worker.version == worker.version)
            .values(is_active=False, status=WorkerStatus.offline, version=Worker.version + 1, updated_at=utcnow())
            .execution_options(synchronize_session=False)
        )
        if result.rowcount != 1:
            raise _version_conflict(worker_id, worker.version)

        session.add(Event(event_type="worker_deactivated", worker_id=worker_id, payload={"name": worker.name}))
        session.commit()
    except Exception:
        session.rollback()
        raise

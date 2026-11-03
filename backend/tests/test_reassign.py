"""POST /api/v1/tasks/{task_id}/reassign: the supervisor's manual override."""
import pytest
from sqlalchemy import select

from app.core.database import SessionLocal
from app.modules.assignment.models import Assignment, AssignmentOutcome, AssignmentSource
from app.modules.events.models import Event
from app.modules.tasks.models import Task, TaskStatus
from app.modules.workforce.models import Worker, WorkerStatus


def url(task_id):
    return f"/api/v1/tasks/{task_id}/reassign"


def fresh(model, id_):
    with SessionLocal() as session:
        return session.get(model, id_)


@pytest.fixture
def held(floor):
    """An assigned task (version 1) held by a busy worker, plus an idle worker to move it to."""
    task = floor.task(2, 2, status=TaskStatus.assigned)
    with SessionLocal() as s:  # as if the assigner had moved it: version 0 -> 1
        s.get(Task, task.id).version = 1
        s.commit()
    old = floor.worker(0, 0, status=WorkerStatus.busy)
    new = floor.worker(5, 5)
    assignment = floor.assign(task, old)
    return {"task": task, "old": old, "new": new, "assignment": assignment}


def assert_conflict(response, code):
    assert response.status_code == 409, response.text
    assert response.json()["code"] == code


def assert_unchanged(held):
    task = fresh(Task, held["task"].id)
    assert (task.status, task.version) == (TaskStatus.assigned, 1)
    assert fresh(Assignment, held["assignment"].id).ended_at is None
    assert fresh(Worker, held["old"].id).status == WorkerStatus.busy


# --- moving an assigned task ---------------------------------------------------------------------


def test_reassign_moves_task_to_new_worker(client, db, held):
    response = client.post(
        url(held["task"].id), json={"worker_id": held["new"].id, "expected_version": 1, "reason": "behind on zone B"}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["task_id"], body["status"], body["version"]) == (held["task"].id, "assigned", 2)
    assert body["assignment"]["worker_id"] == held["new"].id
    assert body["assignment"]["source"] == "supervisor"
    assert body["previous_assignment"]["assignment_id"] == held["assignment"].id
    assert body["previous_assignment"]["worker_id"] == held["old"].id
    assert body["previous_assignment"]["outcome"] == "reassigned"
    assert body["previous_assignment"]["ended_at"] == body["assignment"]["assigned_at"]

    previous = fresh(Assignment, held["assignment"].id)
    assert previous.outcome == AssignmentOutcome.reassigned and previous.ended_at is not None
    new = fresh(Assignment, body["assignment"]["assignment_id"])
    assert (new.task_id, new.worker_id, new.source, new.ended_at) == (
        held["task"].id, held["new"].id, AssignmentSource.supervisor, None
    )
    assert fresh(Worker, held["old"].id).status == WorkerStatus.idle
    assert fresh(Worker, held["new"].id).status == WorkerStatus.busy

    db.rollback()
    [event] = db.scalars(select(Event)).all()
    assert event.event_type == "task_reassigned"
    assert (event.task_id, event.worker_id, event.assignment_id) == (held["task"].id, held["new"].id, new.id)
    assert event.payload == {
        "source": "supervisor",
        "reason": "behind on zone B",
        "previous_assignment_id": held["assignment"].id,
        "previous_worker_id": held["old"].id,
    }


def test_history_keeps_both_assignments(client, db, held):
    client.post(url(held["task"].id), json={"worker_id": held["new"].id, "expected_version": 1})

    db.rollback()
    rows = db.scalars(select(Assignment).where(Assignment.task_id == held["task"].id).order_by(Assignment.id)).all()
    assert [(a.worker_id, a.outcome) for a in rows] == [
        (held["old"].id, AssignmentOutcome.reassigned),
        (held["new"].id, None),
    ]


def test_task_list_shows_the_new_worker(client, held):
    client.post(url(held["task"].id), json={"worker_id": held["new"].id, "expected_version": 1})

    [item] = client.get("/api/v1/tasks", params={"status": "assigned"}).json()["items"]
    assert item["current_assignment"]["worker_id"] == held["new"].id
    assert item["current_assignment"]["source"] == "supervisor"


def test_freed_worker_is_picked_up_by_the_assigner(client, floor, held):
    waiting = floor.task(0, 1)
    client.post(url(held["task"].id), json={"worker_id": held["new"].id, "expected_version": 1})

    made = client.post("/api/v1/assignments/run", json={}).json()["assignments"]

    assert [(a["worker_id"], a["task_id"]) for a in made] == [(held["old"].id, waiting.id)]


def test_old_worker_marked_down_stays_down(client, held):
    with SessionLocal() as s:
        s.get(Worker, held["old"].id).status = WorkerStatus.down
        s.commit()

    client.post(url(held["task"].id), json={"worker_id": held["new"].id, "expected_version": 1})

    assert fresh(Worker, held["old"].id).status == WorkerStatus.down


# --- assigning a task with no current assignment -------------------------------------------------


@pytest.mark.parametrize("status", [TaskStatus.open, TaskStatus.exception])
def test_task_without_assignment_is_assigned_directly(client, db, floor, status):
    task = floor.task(1, 1, status=status)
    worker = floor.worker(0, 0)

    response = client.post(url(task.id), json={"worker_id": worker.id, "expected_version": 0})

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["status"], body["version"], body["previous_assignment"]) == ("assigned", 1, None)
    assert body["assignment"]["worker_id"] == worker.id
    assert fresh(Worker, worker.id).status == WorkerStatus.busy
    db.rollback()
    [event] = db.scalars(select(Event)).all()
    assert event.event_type == "task_assigned"
    assert event.payload["source"] == "supervisor"
    assert event.payload["previous_assignment_id"] is None


# --- rejections (nothing changes) ----------------------------------------------------------------


@pytest.mark.parametrize(
    "status,is_active",
    [(WorkerStatus.busy, True), (WorkerStatus.down, True), (WorkerStatus.offline, True), (WorkerStatus.idle, False)],
    ids=["busy", "down", "offline", "inactive"],
)
def test_unavailable_target_worker_is_409(client, floor, held, status, is_active):
    target = floor.worker(9, 9, status=status, is_active=is_active)

    response = client.post(url(held["task"].id), json={"worker_id": target.id, "expected_version": 1})

    assert_conflict(response, "worker_unavailable")
    assert_unchanged(held)


def test_reassign_to_the_current_worker_is_409(client, held):
    response = client.post(url(held["task"].id), json={"worker_id": held["old"].id, "expected_version": 1})

    assert_conflict(response, "worker_unavailable")
    assert_unchanged(held)


def test_stale_version_is_409(client, held):
    response = client.post(url(held["task"].id), json={"worker_id": held["new"].id, "expected_version": 0})

    assert_conflict(response, "version_conflict")
    assert_unchanged(held)
    assert fresh(Worker, held["new"].id).status == WorkerStatus.idle


def test_picked_task_is_409(client, floor):
    task = floor.task(1, 1, status=TaskStatus.picked)
    worker = floor.worker(0, 0)

    response = client.post(url(task.id), json={"worker_id": worker.id, "expected_version": 0})

    assert_conflict(response, "invalid_transition")
    assert fresh(Worker, worker.id).status == WorkerStatus.idle


def test_unique_key_race_is_409(client, db, floor):
    """Target worker shows idle but already holds an open assignment: the unique key refuses."""
    other = floor.task(9, 9, status=TaskStatus.assigned)
    task = floor.task(1, 1)
    worker = floor.worker(0, 0)
    floor.assign(other, worker)

    response = client.post(url(task.id), json={"worker_id": worker.id, "expected_version": 0})

    assert_conflict(response, "assignment_conflict")
    assert fresh(Task, task.id).status == TaskStatus.open


def test_missing_task_is_404(client, floor):
    worker = floor.worker(0, 0)

    response = client.post(url(9999), json={"worker_id": worker.id, "expected_version": 0})

    assert response.status_code == 404
    assert response.json()["code"] == "task_not_found"


def test_missing_worker_is_404(client, held):
    response = client.post(url(held["task"].id), json={"worker_id": 9999, "expected_version": 1})

    assert response.status_code == 404
    assert response.json()["code"] == "worker_not_found"
    assert_unchanged(held)


@pytest.mark.parametrize(
    "body",
    [{}, {"worker_id": 1}, {"expected_version": 0}, {"worker_id": 1, "expected_version": -1},
     {"worker_id": 1, "expected_version": 0, "reason": "x" * 256}],
    ids=["empty", "no-version", "no-worker", "negative-version", "reason-too-long"],
)
def test_bad_body_is_422(client, held, body):
    response = client.post(url(held["task"].id), json=body)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"

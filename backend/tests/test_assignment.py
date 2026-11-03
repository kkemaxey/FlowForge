"""POST /api/v1/assignments/run, the greedy planner, and the background loop."""
import asyncio
from datetime import datetime

import pytest
from sqlalchemy import select, update

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.assignment import loop as assigner_loop_module
from app.modules.assignment import service
from app.modules.assignment.models import Assignment, AssignmentSource
from app.modules.events.models import Event
from app.modules.simulation.models import SimRun
from app.modules.tasks.models import Task, TaskStatus
from app.modules.workforce.models import Worker, WorkerStatus

URL = "/api/v1/assignments/run"
T0 = datetime(2026, 11, 3, 12, 0, 0)


def pairs(response):
    return [(a["worker_id"], a["task_id"]) for a in response.json()["assignments"]]


def fresh(model, id_):
    with SessionLocal() as session:
        return session.get(model, id_)


# --- choosing pairings ---------------------------------------------------------------------------


def test_each_worker_gets_nearest_task(client, floor):
    near = floor.task(1, 1)
    far = floor.task(8, 8)
    worker = floor.worker(0, 0)

    response = client.post(URL, json={})

    assert response.status_code == 200, response.text
    assert pairs(response) == [(worker.id, near.id)]
    assert response.json()["assignments"][0]["score"] == 2.0  # |0-1| + |0-1|
    assert fresh(Task, far.id).status == TaskStatus.open


def test_workers_take_turns_in_id_order(client, floor):
    a = floor.task(2, 0)
    b = floor.task(5, 0)
    first = floor.worker(4, 0)  # nearest is b (1 away)
    second = floor.worker(3, 0)  # b is taken, so a (1 away)

    response = client.post(URL, json={})

    assert pairs(response) == [(first.id, b.id), (second.id, a.id)]


def test_more_tasks_than_workers_leaves_the_rest_open(client, floor):
    tasks = [floor.task(i, 0) for i in range(4)]
    floor.worker(0, 0)
    floor.worker(9, 9)

    response = client.post(URL, json={})

    assert len(pairs(response)) == 2
    statuses = [fresh(Task, t.id).status for t in tasks]
    assert statuses.count(TaskStatus.assigned) == 2
    assert statuses.count(TaskStatus.open) == 2


def test_more_workers_than_tasks_leaves_the_rest_idle(client, floor):
    task = floor.task(0, 0)
    workers = [floor.worker(i, 0) for i in range(3)]

    response = client.post(URL, json={})

    assert pairs(response) == [(workers[0].id, task.id)]
    assert [fresh(Worker, w.id).status for w in workers] == [WorkerStatus.busy, WorkerStatus.idle, WorkerStatus.idle]


@pytest.mark.parametrize(
    "status,is_active",
    [(WorkerStatus.busy, True), (WorkerStatus.down, True), (WorkerStatus.offline, True), (WorkerStatus.idle, False)],
    ids=["busy", "down", "offline", "inactive"],
)
def test_unavailable_workers_are_skipped(client, floor, status, is_active):
    floor.task(0, 0)
    floor.worker(0, 0, status=status, is_active=is_active)

    response = client.post(URL, json={})

    assert response.json() == {"algorithm": "greedy_v1", "assignments": [], "conflicts": 0}


def test_only_open_tasks_are_assigned(client, floor):
    floor.task(1, 1, status=TaskStatus.picked)
    floor.task(1, 2, status=TaskStatus.exception)
    open_task = floor.task(9, 9)
    worker = floor.worker(1, 1)

    assert pairs(client.post(URL, json={})) == [(worker.id, open_task.id)]


def test_distance_ties_go_to_the_oldest_task(client, floor):
    newer = floor.task(1, 0, minutes=5)
    older = floor.task(0, 1, minutes=0)
    worker = floor.worker(0, 0)

    assert pairs(client.post(URL, json={})) == [(worker.id, older.id)]
    assert fresh(Task, newer.id).status == TaskStatus.open


def test_priority_does_not_change_who_is_assigned(client, floor):
    """greedy_v1 is pure distance: an expedited (high-priority) task loses to a nearer one."""
    near_normal = floor.task(1, 0, priority=0)
    floor.task(9, 9, priority=50)
    worker = floor.worker(0, 0)

    assert pairs(client.post(URL, json={})) == [(worker.id, near_normal.id)]


def test_nothing_to_do(client, db):
    assert client.post(URL, json={}).json() == {"algorithm": "greedy_v1", "assignments": [], "conflicts": 0}


# --- what a pairing writes -----------------------------------------------------------------------


def test_pairing_updates_task_worker_assignment_and_event_together(client, db, floor):
    task = floor.task(3, 4)
    worker = floor.worker(0, 0)

    [made] = client.post(URL, json={}).json()["assignments"]

    stored_task = fresh(Task, task.id)
    assert (stored_task.status, stored_task.version) == (TaskStatus.assigned, 1)
    assert fresh(Worker, worker.id).status == WorkerStatus.busy

    assignment = fresh(Assignment, made["assignment_id"])
    assert (assignment.task_id, assignment.worker_id) == (task.id, worker.id)
    assert assignment.source == AssignmentSource.scheduler
    assert assignment.algorithm == "greedy_v1"
    assert assignment.score == 7.0
    assert assignment.ended_at is None and assignment.outcome is None
    assert made["source"] == "scheduler"
    assert made["assigned_at"].endswith("Z")

    db.rollback()
    [event] = db.scalars(select(Event)).all()
    assert event.event_type == "task_assigned"
    assert (event.task_id, event.worker_id, event.assignment_id, event.order_id) == (
        task.id, worker.id, assignment.id, floor.order_id
    )
    assert event.run_id == floor.run_id  # taken from the task's order
    assert event.payload == {"source": "scheduler", "algorithm": "greedy_v1", "score": 7.0}


def test_request_run_id_tags_events(client, db, floor):
    other_run = SimRun(algorithm="greedy_v1", seed=2, order_rate=1.0)
    db.add(other_run)
    db.commit()
    floor.task(0, 0)
    floor.worker(0, 0)

    client.post(URL, json={"run_id": other_run.id})

    db.rollback()
    assert db.scalar(select(Event.run_id)) == other_run.id


def test_assigned_tasks_show_as_current_assignment(client, floor):
    task = floor.task(0, 0)
    worker = floor.worker(0, 0)
    client.post(URL, json={})

    [item] = client.get("/api/v1/tasks", params={"status": "assigned"}).json()["items"]

    assert item["task_id"] == task.id
    assert item["current_assignment"]["worker_id"] == worker.id


def test_second_pass_assigns_nothing_new(client, floor):
    floor.task(0, 0)
    floor.worker(0, 0)

    client.post(URL, json={})

    assert client.post(URL, json={}).json()["assignments"] == []


def test_empty_body_is_allowed(client, floor):
    floor.task(0, 0)
    floor.worker(0, 0)

    response = client.post(URL)

    assert response.status_code == 200
    assert len(response.json()["assignments"]) == 1


# --- conflicts -----------------------------------------------------------------------------------


def interfere_after_planning(monkeypatch, interference):
    """Run `interference` in another session after the pass has planned but before it writes."""
    real = service.ALGORITHMS["greedy_v1"]

    def planner(workers, tasks):
        plan = real(workers, tasks)
        with SessionLocal() as other:
            interference(other)
            other.commit()
        return plan

    monkeypatch.setitem(service.ALGORITHMS, "greedy_v1", planner)


def test_task_changed_mid_pass_counts_as_conflict(client, db, floor, monkeypatch):
    raced = floor.task(0, 0)
    other = floor.task(5, 5)
    w1 = floor.worker(0, 0)
    w2 = floor.worker(5, 5)
    interfere_after_planning(
        monkeypatch, lambda s: s.execute(update(Task).where(Task.id == raced.id).values(version=Task.version + 1))
    )

    response = client.post(URL, json={})

    assert response.json()["conflicts"] == 1
    assert pairs(response) == [(w2.id, other.id)]  # the other pairing still went through
    assert fresh(Task, raced.id).status == TaskStatus.open
    assert fresh(Worker, w1.id).status == WorkerStatus.idle  # rolled back with the task
    db.rollback()
    assert db.scalars(select(Assignment.task_id)).all() == [other.id]
    assert db.scalars(select(Event.task_id)).all() == [other.id]


def test_worker_changed_mid_pass_counts_as_conflict(client, db, floor, monkeypatch):
    task = floor.task(0, 0)
    worker = floor.worker(0, 0)
    interfere_after_planning(
        monkeypatch, lambda s: s.execute(update(Worker).where(Worker.id == worker.id).values(status=WorkerStatus.down))
    )

    response = client.post(URL, json={})

    assert response.json()["conflicts"] == 1
    stored = fresh(Task, task.id)
    assert (stored.status, stored.version) == (TaskStatus.open, 0)  # task change rolled back too
    db.rollback()
    assert db.scalars(select(Assignment)).all() == []


def test_open_assignment_unique_key_counts_as_conflict(client, db, floor):
    """A worker marked idle but still holding an open assignment: the unique key rejects a second."""
    held = floor.task(9, 9, status=TaskStatus.assigned)
    task = floor.task(0, 0)
    worker = floor.worker(0, 0)
    db.add(Assignment(task_id=held.id, worker_id=worker.id, source=AssignmentSource.supervisor))
    db.commit()

    response = client.post(URL, json={})

    assert response.json() == {"algorithm": "greedy_v1", "assignments": [], "conflicts": 1}
    assert fresh(Task, task.id).status == TaskStatus.open


def test_conflicted_task_is_assigned_next_pass(client, floor, monkeypatch):
    task = floor.task(0, 0)
    floor.worker(0, 0)
    interfere_after_planning(
        monkeypatch, lambda s: s.execute(update(Task).where(Task.id == task.id).values(version=Task.version + 1))
    )
    assert client.post(URL, json={}).json()["conflicts"] == 1
    monkeypatch.undo()

    assert [t for _, t in pairs(client.post(URL, json={}))] == [task.id]


# --- request validation --------------------------------------------------------------------------


def test_unknown_algorithm_is_422(client, db):
    response = client.post(URL, json={"algorithm": "magic"})

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_algorithm"


def test_unknown_run_is_422(client, db):
    response = client.post(URL, json={"run_id": 999})

    assert response.status_code == 422
    assert response.json()["code"] == "unknown_run"


# --- background loop -----------------------------------------------------------------------------


def test_loop_is_off_in_tests():
    assert settings.assigner_loop_enabled is False


def test_loop_assigns_new_tasks_until_stopped(db, floor):
    worker = floor.worker(0, 0)
    floor.task(0, 0)

    async def scenario():
        stop = asyncio.Event()
        running = asyncio.create_task(assigner_loop_module.assigner_loop(0.05, stop))
        await asyncio.sleep(0.3)
        assert fresh(Worker, worker.id).status == WorkerStatus.busy  # first task taken
        late = floor.task(1, 1)  # arrives while the loop is running
        with SessionLocal() as s:  # finish the first pick so the worker is free again
            s.execute(update(Worker).where(Worker.id == worker.id).values(status=WorkerStatus.idle))
            s.execute(update(Assignment).values(ended_at=T0))
            s.commit()
        await asyncio.sleep(0.3)
        stop.set()
        await asyncio.wait_for(running, timeout=2)
        return late

    late = asyncio.run(scenario())

    assert fresh(Task, late.id).status == TaskStatus.assigned
    db.rollback()
    assert len(db.scalars(select(Assignment)).all()) == 2


def test_loop_survives_a_failing_pass(monkeypatch):
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("database hiccup")

    monkeypatch.setattr(assigner_loop_module, "run_once", flaky)

    async def scenario():
        stop = asyncio.Event()
        running = asyncio.create_task(assigner_loop_module.assigner_loop(0.01, stop))
        await asyncio.sleep(0.1)
        stop.set()
        await asyncio.wait_for(running, timeout=2)

    asyncio.run(scenario())

    assert len(calls) > 1

from datetime import timedelta


from app.core.database import utcnow
from app.modules.simulation.models import TaskException
from tests.sim_fixtures import api, build_world, db, db_engine, session_factory  # noqa: F401


def add_exception(db, world, *, type="jam", opened_ago_s=0, resolved=False) -> TaskException:
    exc = TaskException(
        type=type, task_id=world.task.id, assignment_id=world.assignment.id,
        from_location_id=world.bin_a.id, opened_at=utcnow() - timedelta(seconds=opened_ago_s),
        resolved_at=utcnow() if resolved else None,
    )
    db.add(exc)
    db.commit()
    return exc


def test_open_true_lists_only_unresolved_newest_first(api, db):
    world = build_world(db)
    older = add_exception(db, world, opened_ago_s=60)
    newer = add_exception(db, world, type="stockout", opened_ago_s=5)
    add_exception(db, world, resolved=True)

    response = api.get("/api/v1/exceptions", params={"open": "true"})

    assert response.status_code == 200
    body = response.json()
    assert [e["exception_id"] for e in body] == [newer.id, older.id]
    assert body[0]["type"] == "stockout"
    assert body[0]["order_id"] == world.order.id
    assert body[0]["task_status"] == "assigned"
    assert body[0]["resolved_at"] is None
    assert body[0]["opened_at"].endswith("Z")


def test_open_false_and_omitted(api, db):
    world = build_world(db)
    add_exception(db, world)
    resolved = add_exception(db, world, resolved=True)

    assert [e["exception_id"] for e in api.get("/api/v1/exceptions?open=false").json()] == [resolved.id]
    assert len(api.get("/api/v1/exceptions").json()) == 2


def test_unrecoverable_exception_is_open(api, db):
    world = build_world(db, near_stock=0, far_stock=0)
    created = api.post(
        f"/api/v1/tasks/{world.task.id}/exceptions", json={"type": "stockout", "assignment_id": world.assignment.id, "qty_found": 0}
    ).json()

    listed = api.get("/api/v1/exceptions?open=true").json()

    assert [e["exception_id"] for e in listed] == [created["exception_id"]]
    assert (listed[0]["task_status"], listed[0]["rerouted_to_location_id"]) == ("exception", None)


def test_rerouted_exception_is_resolved_not_open(api, db):
    world = build_world(db)
    created = api.post(
        f"/api/v1/tasks/{world.task.id}/exceptions", json={"type": "stockout", "assignment_id": world.assignment.id, "qty_found": 0}
    ).json()

    assert api.get("/api/v1/exceptions?open=true").json() == []
    resolved = api.get("/api/v1/exceptions?open=false").json()
    assert [e["exception_id"] for e in resolved] == [created["exception_id"]]
    assert resolved[0]["rerouted_to_location_id"] == world.bin_near.id
    assert resolved[0]["resolved_at"] == resolved[0]["opened_at"]


def test_empty_list(api, db):
    assert api.get("/api/v1/exceptions?open=true").json() == []


def test_bad_params_are_422(api, db):
    for query in ("open=maybe", "limit=0", "limit=501"):
        response = api.get(f"/api/v1/exceptions?{query}")
        assert response.status_code == 422, query
        assert response.json()["code"] == "validation_error"

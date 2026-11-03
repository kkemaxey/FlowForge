"""/api/v1/workers: CRUD, soft delete and version checks, against the MySQL test database."""
import pytest
from sqlalchemy import select

from app.modules.events.models import Event
from app.modules.warehouse.models import Location, LocationKind
from app.modules.workforce.models import Worker, WorkerStatus

URL = "/api/v1/workers"


@pytest.fixture
def grid(db):
    """Two locations that make the grid 10 x 6 (x 0..9, y 0..5)."""
    db.add_all(
        [
            Location(x=0, y=0, kind=LocationKind.pick_station),
            Location(x=9, y=5, kind=LocationKind.storage),
        ]
    )
    db.commit()


def create(client, **overrides):
    body = {"name": "Ada", "kind": "human", "x": 1, "y": 2, "speed": 1.5} | overrides
    return client.post(URL, json=body)


def events(db, event_type):
    db.rollback()  # see rows the API request committed
    return db.scalars(select(Event).where(Event.event_type == event_type).order_by(Event.id)).all()


def fresh(db, worker_id):
    """The worker as committed now. rollback() alone doesn't expire objects cached without a transaction."""
    db.rollback()
    db.expire_all()
    return db.get(Worker, worker_id)


def ids(response):
    return [item["worker_id"] for item in response.json()["items"]]


# --- POST /api/v1/workers ------------------------------------------------------------------------


def test_create_returns_201_location_and_body(client, db):
    response = create(client)

    assert response.status_code == 201
    body = response.json()
    assert response.headers["location"] == f"{URL}/{body['worker_id']}"
    assert body | {"worker_id": 0, "created_at": "", "updated_at": ""} == {
        "worker_id": 0,
        "name": "Ada",
        "kind": "human",
        "status": "idle",
        "x": 1,
        "y": 2,
        "speed": 1.5,
        "is_active": True,
        "version": 0,
        "created_at": "",
        "updated_at": "",
    }
    assert body["created_at"].endswith("Z")
    assert body["updated_at"].endswith("Z")

    [event] = events(db, "worker_created")
    assert event.worker_id == body["worker_id"]
    assert event.payload == {"name": "Ada", "kind": "human", "x": 1, "y": 2, "speed": 1.5}


def test_create_defaults_speed_to_one(client, db):
    response = client.post(URL, json={"name": "R2", "kind": "robot", "x": 0, "y": 0})

    assert response.status_code == 201
    assert response.json()["speed"] == 1.0


def test_create_off_grid_is_422(client, db, grid):
    response = create(client, x=10, y=0)

    assert response.status_code == 422
    assert response.json()["code"] == "position_off_grid"
    assert "(10, 0)" in response.json()["detail"]
    assert "10 x 6" in response.json()["detail"]
    db.rollback()
    assert db.scalars(select(Worker)).all() == []


def test_create_on_grid_edge_is_accepted(client, db, grid):
    assert create(client, x=9, y=5).status_code == 201


@pytest.mark.parametrize("field", ["status", "is_active", "version"])
def test_create_rejects_server_owned_fields(client, db, field):
    value = {"status": "busy", "is_active": False, "version": 7}[field]
    response = create(client, **{field: value})

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"name": "   "},  # stripped to blank
        {"name": "x" * 65},
        {"kind": "drone"},
        {"speed": 0},
        {"speed": -1},
        {"speed": 100},
        {"x": -1},
        {"y": -1},
    ],
)
def test_create_validation_errors(client, db, overrides):
    response = create(client, **overrides)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


def test_create_stores_sql_injection_style_name_verbatim(client, db):
    name = "Robert'); DROP TABLE workers;--"
    response = create(client, name=name)

    assert response.status_code == 201
    assert fresh(db, response.json()["worker_id"]).name == name


# --- GET /api/v1/workers -------------------------------------------------------------------------


def test_list_hides_inactive_by_default(client, floor):
    active = floor.worker(1, 1)
    inactive = floor.worker(2, 2, is_active=False)

    response = client.get(URL)

    assert response.status_code == 200
    assert ids(response) == [active.id]
    assert response.json()["count"] == 1

    response = client.get(URL, params={"include_inactive": "true"})
    assert ids(response) == [active.id, inactive.id]
    assert response.json()["count"] == 2


def test_list_filters_status_and_kind(client, db, floor):
    idle = floor.worker(1, 1)
    busy = floor.worker(2, 2, status=WorkerStatus.busy)
    robot = Worker(name="R", kind="robot", x=3, y=3)
    db.add(robot)
    db.commit()

    assert ids(client.get(URL, params={"status": "busy"})) == [busy.id]
    assert ids(client.get(URL, params={"kind": "robot"})) == [robot.id]
    assert ids(client.get(URL, params={"status": "idle", "kind": "human"})) == [idle.id]


def test_list_limit(client, floor):
    workers = [floor.worker(n, n) for n in range(3)]

    response = client.get(URL, params={"limit": 2})

    assert ids(response) == [workers[0].id, workers[1].id]
    assert response.json()["count"] == 2


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 501}, {"status": "asleep"}, {"kind": "drone"}])
def test_list_bad_query_is_422(client, db, params):
    response = client.get(URL, params=params)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


# --- GET /api/v1/workers/{id} --------------------------------------------------------------------


def test_get_includes_inactive(client, floor):
    worker = floor.worker(1, 1, is_active=False)

    response = client.get(f"{URL}/{worker.id}")

    assert response.status_code == 200
    assert response.json()["worker_id"] == worker.id
    assert response.json()["is_active"] is False


def test_get_unknown_is_404(client, db):
    response = client.get(f"{URL}/999999")

    assert response.status_code == 404
    assert response.json()["code"] == "worker_not_found"


# --- PATCH /api/v1/workers/{id} ------------------------------------------------------------------


def test_patch_updates_bumps_version_and_writes_event(client, db, floor):
    worker = floor.worker(1, 1)
    before = client.get(f"{URL}/{worker.id}").json()

    response = client.patch(
        f"{URL}/{worker.id}", json={"expected_version": 0, "name": "Grace", "x": 4, "y": 1, "speed": 2.0}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Grace"
    assert (body["x"], body["y"], body["speed"]) == (4, 1, 2.0)
    assert body["version"] == 1
    assert body["updated_at"] >= before["updated_at"]

    [event] = events(db, "worker_updated")
    assert event.worker_id == worker.id
    # Only fields that actually changed (y stayed 1).
    assert event.payload == {"changes": {"name": "Grace", "x": 4, "speed": 2.0}}
    assert fresh(db, worker.id).version == 1


def test_patch_empty_change_set_returns_worker_unchanged(client, db, floor):
    worker = floor.worker(1, 1)

    response = client.patch(f"{URL}/{worker.id}", json={"expected_version": 0})

    assert response.status_code == 200
    assert response.json()["version"] == 0
    assert events(db, "worker_updated") == []


def test_patch_same_values_is_not_a_change(client, db, floor):
    worker = floor.worker(1, 1)

    response = client.patch(f"{URL}/{worker.id}", json={"expected_version": 0, "x": 1})

    assert response.status_code == 200
    assert response.json()["version"] == 0
    assert events(db, "worker_updated") == []


def test_patch_empty_change_set_still_checks_version(client, db, floor):
    worker = floor.worker(1, 1)

    response = client.patch(f"{URL}/{worker.id}", json={"expected_version": 3})

    assert response.status_code == 409
    assert response.json()["code"] == "version_conflict"


def test_patch_stale_version_is_409(client, db, floor):
    worker = floor.worker(1, 1)
    assert client.patch(f"{URL}/{worker.id}", json={"expected_version": 0, "name": "A"}).status_code == 200

    response = client.patch(f"{URL}/{worker.id}", json={"expected_version": 0, "name": "B"})

    assert response.status_code == 409
    assert response.json()["code"] == "version_conflict"
    assert fresh(db, worker.id).name == "A"
    assert len(events(db, "worker_updated")) == 1


def test_patch_moving_busy_worker_is_409(client, db, floor):
    worker = floor.worker(1, 1, status=WorkerStatus.busy)

    response = client.patch(f"{URL}/{worker.id}", json={"expected_version": 0, "x": 2})

    assert response.status_code == 409
    assert response.json()["code"] == "worker_busy"


def test_patch_busy_worker_name_is_allowed(client, db, floor):
    worker = floor.worker(1, 1, status=WorkerStatus.busy)

    response = client.patch(f"{URL}/{worker.id}", json={"expected_version": 0, "name": "Renamed"})

    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_patch_inactive_worker_is_409(client, db, floor):
    worker = floor.worker(1, 1, is_active=False)

    response = client.patch(f"{URL}/{worker.id}", json={"expected_version": 0, "name": "X"})

    assert response.status_code == 409
    assert response.json()["code"] == "worker_inactive"


def test_patch_off_grid_is_422(client, db, floor, grid):
    worker = floor.worker(1, 1)

    response = client.patch(f"{URL}/{worker.id}", json={"expected_version": 0, "y": 6})

    assert response.status_code == 422
    assert response.json()["code"] == "position_off_grid"


def test_patch_unknown_is_404(client, db):
    response = client.patch(f"{URL}/999999", json={"expected_version": 0, "name": "X"})

    assert response.status_code == 404
    assert response.json()["code"] == "worker_not_found"


@pytest.mark.parametrize(
    "body",
    [
        {"expected_version": 0, "name": None},
        {"expected_version": 0, "x": None},
        {"expected_version": 0, "speed": None},
        {"name": "No version"},
        {"expected_version": -1},
        {"expected_version": 0, "status": "busy"},
        {"expected_version": 0, "is_active": True},
        {"expected_version": 0, "speed": 0},
    ],
)
def test_patch_validation_errors(client, db, floor, body):
    worker = floor.worker(1, 1)

    response = client.patch(f"{URL}/{worker.id}", json=body)

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


# --- DELETE /api/v1/workers/{id} -----------------------------------------------------------------


def test_delete_soft_deletes(client, db, floor):
    worker = floor.worker(1, 1)

    response = client.delete(f"{URL}/{worker.id}")

    assert response.status_code == 204
    assert response.content == b""
    row = fresh(db, worker.id)
    assert row is not None
    assert row.is_active is False
    assert row.status == WorkerStatus.offline
    assert row.version == 1
    [event] = events(db, "worker_deactivated")
    assert event.worker_id == worker.id


def test_delete_with_open_assignment_is_409(client, db, floor):
    worker = floor.worker(1, 1, status=WorkerStatus.busy)
    floor.assign(floor.task(2, 2), worker)

    response = client.delete(f"{URL}/{worker.id}")

    assert response.status_code == 409
    assert response.json()["code"] == "worker_has_open_assignment"
    assert fresh(db, worker.id).is_active is True


def test_delete_twice_is_204_with_one_event(client, db, floor):
    worker = floor.worker(1, 1)

    assert client.delete(f"{URL}/{worker.id}").status_code == 204
    assert client.delete(f"{URL}/{worker.id}").status_code == 204

    assert len(events(db, "worker_deactivated")) == 1
    assert fresh(db, worker.id).version == 1


def test_delete_unknown_is_404(client, db):
    response = client.delete(f"{URL}/999999")

    assert response.status_code == 404
    assert response.json()["code"] == "worker_not_found"


def test_deleted_worker_drops_out_of_list(client, floor):
    worker = floor.worker(1, 1)
    client.delete(f"{URL}/{worker.id}")

    assert ids(client.get(URL)) == []

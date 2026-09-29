from app.modules.workforce.models import WorkerRow

NEW_WORKER = {"name": "Ana", "type": "human", "speed": 1.5, "cur_x": 3, "cur_y": 4}


def create_worker(client, **overrides):
    body = dict(NEW_WORKER)
    body.update(overrides)
    response = client.post("/api/workers", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def insert_busy_worker(app) -> int:
    with app.state.session_factory() as session:
        row = WorkerRow(name="Busy Bee", type="robot", speed=2.0, cur_x=1, cur_y=1,
                        status="busy", enabled=True)
        session.add(row)
        session.commit()
        return row.id


def test_create_worker_returns_201_with_location(client):
    response = client.post("/api/workers", json=NEW_WORKER)

    assert response.status_code == 201
    body = response.json()
    assert body == {**NEW_WORKER, "id": body["id"], "status": "idle", "enabled": True}
    assert response.headers["Location"] == f"/api/workers/{body['id']}"


def test_create_worker_off_grid_is_rejected(client):
    response = client.post("/api/workers", json={**NEW_WORKER, "cur_x": 20})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "position_off_grid"


def test_create_worker_cannot_set_status(client):
    response = client.post("/api/workers", json={**NEW_WORKER, "status": "busy"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert "status" in response.json()["error"]["message"]


def test_create_worker_rejects_blank_name_bad_type_and_speed(client):
    for bad_field in ({"name": "   "}, {"type": "drone"}, {"speed": 0}, {"speed": 11}):
        response = client.post("/api/workers", json={**NEW_WORKER, **bad_field})
        assert response.status_code == 422, bad_field
        assert response.json()["error"]["code"] == "validation_error"


def test_list_and_filter_workers(client):
    create_worker(client, name="Ana", type="human")
    create_worker(client, name="R1", type="robot")

    all_workers = client.get("/api/workers").json()
    robots = client.get("/api/workers", params={"type": "robot"}).json()

    assert [w["name"] for w in all_workers] == ["Ana", "R1"]
    assert [w["name"] for w in robots] == ["R1"]


def test_get_missing_worker_returns_404(client):
    response = client.get("/api/workers/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "worker_not_found"


def test_patch_updates_only_given_fields(client):
    worker = create_worker(client)

    response = client.patch(f"/api/workers/{worker['id']}", json={"name": "Ana B", "enabled": False})

    assert response.status_code == 200
    assert response.json() == {**worker, "name": "Ana B", "enabled": False}


def test_patch_rejects_null_values(client):
    worker = create_worker(client)

    response = client.patch(f"/api/workers/{worker['id']}", json={"name": None})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_delete_worker_returns_204_then_404(client):
    worker = create_worker(client)

    deleted = client.delete(f"/api/workers/{worker['id']}")
    fetched = client.get(f"/api/workers/{worker['id']}")

    assert deleted.status_code == 204
    assert deleted.content == b""
    assert fetched.status_code == 404


def test_delete_busy_worker_returns_409(app, client):
    worker_id = insert_busy_worker(app)

    response = client.delete(f"/api/workers/{worker_id}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "worker_busy"


def test_sql_injection_attempts_are_treated_as_plain_data(client):
    hostile_name = "Robert'); DROP TABLE workers;--"
    create_worker(client, name=hostile_name)

    filtered = client.get("/api/workers", params={"type": "robot' OR '1'='1"})
    listed = client.get("/api/workers")

    assert filtered.status_code == 422
    assert listed.status_code == 200
    assert [w["name"] for w in listed.json()] == [hostile_name]

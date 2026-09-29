def add_worker(client, **overrides) -> dict:
    body = {"name": "Maria Lopez", "type": "human", "speed": 1.2}
    body.update(overrides)
    response = client.post("/api/workers", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_health_reports_database_connected(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"


def test_created_worker_reads_back_from_the_database(client):
    created = add_worker(client, cur_x=4, cur_y=7)
    assert created == {"id": created["id"], "name": "Maria Lopez", "type": "human",
                       "speed": 1.2, "cur_x": 4, "cur_y": 7, "status": "idle",
                       "enabled": True}

    response = client.get("/api/workers")
    assert response.status_code == 200
    assert response.json() == [created]


def test_list_is_empty_before_anyone_is_added(client):
    assert client.get("/api/workers").json() == []


def test_list_filters_by_type_and_status(client):
    add_worker(client, name="Ana")
    add_worker(client, name="PickBot-1", type="robot", speed=3.0)
    add_worker(client, name="PickBot-2", type="robot", speed=3.0, status="busy")

    robots = client.get("/api/workers", params={"type": "robot"}).json()
    assert [worker["name"] for worker in robots] == ["PickBot-1", "PickBot-2"]
    idle_robots = client.get("/api/workers", params={"type": "robot", "status": "idle"}).json()
    assert [worker["name"] for worker in idle_robots] == ["PickBot-1"]


def test_duplicate_name_returns_409(client):
    add_worker(client)
    response = client.post("/api/workers",
                           json={"name": "MARIA LOPEZ", "type": "human", "speed": 1.0})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert len(client.get("/api/workers").json()) == 1


def test_bad_input_returns_422_naming_each_field(client):
    response = client.post("/api/workers",
                           json={"name": "Maria", "type": "drone", "speed": 1, "cur_x": 25})
    assert response.status_code == 422
    fields = {detail["field"] for detail in response.json()["error"]["details"]}
    assert fields == {"body.type", "body.cur_x"}


def test_business_rule_violation_returns_422(client):
    response = client.post("/api/workers", json={"name": "Speedy", "type": "human", "speed": 3})
    assert response.status_code == 422
    assert "at most 2.0" in response.json()["error"]["message"]


def test_bad_filter_returns_422(client):
    assert client.get("/api/workers", params={"type": "drone"}).status_code == 422


def test_sql_in_input_is_stored_as_plain_text(client):
    name = "Robert'); DROP TABLE workers;--"
    add_worker(client, name=name)
    assert [worker["name"] for worker in client.get("/api/workers").json()] == [name]


def test_every_response_carries_a_request_id(client):
    response = client.get("/api/workers", headers={"X-Request-ID": "demo-123"})
    assert response.headers["X-Request-ID"] == "demo-123"

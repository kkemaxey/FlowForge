from datetime import UTC, datetime, timedelta


def future(minutes: int) -> str:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()


def create_task(client, **overrides) -> dict:
    body = {"order_ref": "ORD-10442", "sku": "SKU-88213", "bin_location": "B-07-3",
            "quantity": 4, "due_at": future(30)}
    body.update(overrides)
    response = client.post("/api/tasks", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_health_reports_database_connected(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"


def test_create_then_read_task_round_trips_through_database(client):
    created = create_task(client)
    assert created["status"] == "open"

    fetched = client.get(f"/api/tasks/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["order_ref"] == "ORD-10442"
    assert [t["id"] for t in client.get("/api/tasks").json()] == [created["id"]]


def test_every_response_carries_a_request_id(client):
    response = client.get("/api/tasks", headers={"X-Request-ID": "demo-123"})
    assert response.headers["X-Request-ID"] == "demo-123"


def test_status_lifecycle_through_api(client):
    task_id = create_task(client)["id"]
    steps = [{"status": "assigned", "worker_id": 2}, {"status": "in_progress"},
             {"status": "picked"}]
    for step in steps:
        response = client.patch(f"/api/tasks/{task_id}/status", json=step)
        assert response.status_code == 200, response.text

    task = response.json()
    assert task["status"] == "picked"
    assert task["completed_at"] is not None
    assert client.get("/api/tasks", params={"status": "picked"}).json()[0]["id"] == task_id


def test_invalid_transition_returns_409(client):
    task_id = create_task(client)["id"]
    response = client.patch(f"/api/tasks/{task_id}/status", json={"status": "picked"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_transition"


def test_missing_task_returns_404(client):
    response = client.get("/api/tasks/9999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_bad_body_returns_422_with_field_details(client):
    response = client.post("/api/tasks", json={"order_ref": "X", "sku": "Y",
                                               "bin_location": "nowhere", "quantity": 0,
                                               "due_at": future(10)})
    assert response.status_code == 422
    fields = {detail["field"] for detail in response.json()["error"]["details"]}
    assert {"body.bin_location", "body.quantity"} <= fields


def test_past_due_time_returns_422(client):
    response = client.post("/api/tasks", json={"order_ref": "X", "sku": "Y",
                                               "bin_location": "A-01-1", "quantity": 1,
                                               "due_at": future(-5)})
    assert response.status_code == 422


def test_injection_style_input_is_stored_as_plain_text(client):
    hostile = "ORD-1'; DROP TABLE pick_tasks; --"
    created = create_task(client, order_ref=hostile)
    assert client.get(f"/api/tasks/{created['id']}").json()["order_ref"] == hostile
    assert len(client.get("/api/tasks").json()) == 1


def test_board_groups_tasks_and_counts_wip(client):
    late_id = create_task(client, order_ref="LATE", due_at=future(1))["id"]
    rush_id = create_task(client, order_ref="RUSH", due_at=future(90))["id"]
    working_id = create_task(client, order_ref="WORK")["id"]

    client.post(f"/api/tasks/{rush_id}/expedite")
    client.patch(f"/api/tasks/{working_id}/status", json={"status": "assigned", "worker_id": 5})

    board = client.get("/api/board").json()
    assert [card["order_ref"] for card in board["columns"]["open"]] == ["RUSH", "LATE"]
    assert [card["id"] for card in board["columns"]["assigned"]] == [working_id]
    assert board["summary"]["work_in_progress"] == 1
    assert board["summary"]["total_tasks"] == 3
    assert late_id in {card["id"] for card in board["columns"]["open"]}


def test_times_are_returned_as_utc_and_match_the_stored_row(client):
    created = create_task(client)
    assert created["due_at"].endswith("Z")
    assert client.get(f"/api/tasks/{created['id']}").json()["due_at"] == created["due_at"]

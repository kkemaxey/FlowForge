from datetime import UTC, datetime, timedelta


def future(minutes: int) -> str:
    return (datetime.now(UTC) + timedelta(minutes=minutes)).isoformat()


def create_order(client, due_in_minutes=30, lines=None, **overrides) -> dict:
    body = {"due_at": future(due_in_minutes),
            "lines": lines or [{"sku_id": "SKU-88213", "qty": 4, "location_id": "A1-01"}]}
    body.update(overrides)
    response = client.post("/api/orders", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def move(client, task_id, **body):
    return client.patch(f"/api/tasks/{task_id}/status", json=body)


def test_health_reports_database_connected(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"


def test_order_intake_generates_tasks_that_read_back_from_database(client):
    order = create_order(client, lines=[
        {"sku_id": "SKU-1", "qty": 2, "location_id": "A1-01"},
        {"sku_id": "SKU-2", "qty": 1, "location_id": "C4-11"},
    ])
    assert order["status"] == "new"
    assert [task["location_id"] for task in order["tasks"]] == ["A1-01", "C4-11"]

    fetched = client.get(f"/api/orders/{order['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == order
    task_id = order["tasks"][1]["id"]
    assert client.get(f"/api/tasks/{task_id}").json()["order_id"] == order["id"]


def test_every_response_carries_a_request_id(client):
    response = client.get("/api/tasks", headers={"X-Request-ID": "demo-123"})
    assert response.headers["X-Request-ID"] == "demo-123"


def test_task_lifecycle_updates_assignment_and_order(client):
    order = create_order(client)
    task_id = order["tasks"][0]["id"]

    assigned = move(client, task_id, status="assigned", worker_id=2)
    assert assigned.status_code == 200
    assert assigned.json()["worker_id"] == 2
    assert client.get(f"/api/orders/{order['id']}").json()["status"] == "in_progress"

    picked = move(client, task_id, status="picked").json()
    assert picked["completed_at"] is not None
    assert client.get(f"/api/orders/{order['id']}").json()["status"] == "complete"
    assert [t["id"] for t in client.get("/api/tasks", params={"status": "picked"}).json()] \
        == [task_id]


def test_exception_and_reassignment_through_api(client):
    task_id = create_order(client)["tasks"][0]["id"]
    move(client, task_id, status="assigned", worker_id=2)
    assert move(client, task_id, status="exception").json()["status"] == "exception"
    assert move(client, task_id, status="open").json()["worker_id"] is None
    assert move(client, task_id, status="assigned", worker_id=5).json()["worker_id"] == 5


def test_invalid_transition_returns_409(client):
    task_id = create_order(client)["tasks"][0]["id"]
    response = move(client, task_id, status="picked")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_transition"


def test_missing_order_and_task_return_404(client):
    assert client.get("/api/orders/9999").status_code == 404
    response = client.get("/api/tasks/9999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_bad_body_returns_422_with_field_details(client):
    response = client.post("/api/orders", json={
        "due_at": future(10),
        "lines": [{"sku_id": "X", "qty": 0, "location_id": "nowhere"}]})
    assert response.status_code == 422
    fields = {detail["field"] for detail in response.json()["error"]["details"]}
    assert {"body.lines.0.qty", "body.lines.0.location_id"} <= fields


def test_empty_order_and_past_due_time_return_422(client):
    assert client.post("/api/orders", json={"due_at": future(10), "lines": []}).status_code == 422
    response = client.post("/api/orders", json={
        "due_at": future(-5), "lines": [{"sku_id": "X", "qty": 1, "location_id": "A1-01"}]})
    assert response.status_code == 422


def test_injection_style_input_is_stored_as_plain_text(client):
    hostile = "SKU'; DROP TABLE tasks; --"
    order = create_order(client, lines=[{"sku_id": hostile, "qty": 1, "location_id": "A1-01"}])
    task_id = order["tasks"][0]["id"]
    assert client.get(f"/api/tasks/{task_id}").json()["sku_id"] == hostile.upper()
    assert len(client.get("/api/tasks").json()) == 1


def test_times_are_returned_as_utc_and_match_the_stored_row(client):
    order = create_order(client)
    assert order["due_at"].endswith("Z")
    assert client.get(f"/api/orders/{order['id']}").json()["due_at"] == order["due_at"]


def test_board_groups_tasks_and_counts_orders(client):
    soon = create_order(client, due_in_minutes=1)
    rush = create_order(client, due_in_minutes=90)
    working = create_order(client)

    client.post(f"/api/orders/{rush['id']}/expedite")
    move(client, working["tasks"][0]["id"], status="assigned", worker_id=5)

    board = client.get("/api/board").json()
    assert [card["order_id"] for card in board["columns"]["open"]] == [rush["id"], soon["id"]]
    assert board["columns"]["assigned"][0]["worker_id"] == 5
    assert board["summary"]["work_in_progress"] == 1
    assert board["orders_by_status"] == {"new": 2, "in_progress": 1, "complete": 0, "late": 0}

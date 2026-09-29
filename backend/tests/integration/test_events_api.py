def post_event(client, **body):
    response = client.post("/api/events", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def test_post_event_returns_201_with_server_timestamp(client):
    body = post_event(client, type="task_picked", task_id=1, worker_id=2, qty=3)

    assert body["id"] >= 1
    assert body["type"] == "task_picked"
    assert body["qty"] == 3
    assert body["ts"]


def test_pick_event_without_qty_is_rejected(client):
    response = client.post("/api/events", json={"type": "task_picked", "task_id": 1})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "qty_required"


def test_unknown_event_type_is_rejected(client):
    response = client.post("/api/events", json={"type": "robot_danced", "task_id": 1})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_events_flow_into_metrics(client):
    client.post("/api/workers", json={"name": "Ana", "type": "human", "speed": 1, "cur_x": 0, "cur_y": 0})
    client.post("/api/workers", json={"name": "R1", "type": "robot", "speed": 2, "cur_x": 1, "cur_y": 1,
                                      "enabled": False})
    for task_id in (1, 2, 3, 4):
        post_event(client, type="task_assigned", task_id=task_id)
    post_event(client, type="task_picked", task_id=1, qty=5)
    post_event(client, type="task_picked", task_id=2, qty=3)
    post_event(client, type="task_exception", task_id=3, payload={"reason": "stockout"})

    response = client.get("/api/metrics", params={"window_minutes": 60})

    assert response.status_code == 200
    assert response.json() == {
        "window_minutes": 60,
        "units_picked": 8,
        "throughput_per_hour": 8.0,
        "wip": 1,
        "exceptions": 1,
        "workers": {"idle": 1, "busy": 0, "disabled": 1},
    }


def test_metrics_default_window_is_60_minutes(client):
    assert client.get("/api/metrics").json()["window_minutes"] == 60


def test_metrics_rejects_out_of_range_window(client):
    response = client.get("/api/metrics", params={"window_minutes": 0})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_window"

from datetime import timedelta

import pytest

from app.core.database import utcnow
from app.modules.events.models import Event
from app.modules.simulation.models import SimRun
from tests.sim_fixtures import api, db, db_engine, session_factory  # noqa: F401


def add_events(db, run_id, type, minutes_ago_list):
    now = utcnow()
    db.add_all(Event(run_id=run_id, type=type, created_at=now - timedelta(minutes=m)) for m in minutes_ago_list)


@pytest.fixture
def runs(db):
    run, other = SimRun(seed=1), SimRun(seed=2)
    db.add_all([run, other])
    db.flush()
    add_events(db, run.id, "task_picked", [0.1, 1, 2, 4.5, 6, 30])   # 4 inside a 5-minute window
    add_events(db, run.id, "task_assigned", [0.5, 1])                 # wrong type
    add_events(db, other.id, "task_picked", [0.5, 1, 2])              # wrong run
    db.commit()
    return run, other


def test_counts_only_this_runs_picks_in_window(api, runs):
    run, _ = runs

    response = api.get("/api/v1/metrics/throughput", params={"run_id": run.id, "window_minutes": 5})

    assert response.status_code == 200
    body = response.json()
    assert (body["run_id"], body["window_minutes"], body["picks"]) == (run.id, 5, 4)
    assert body["picks_per_min"] == 0.8
    assert body["as_of"].endswith("Z")


def test_window_defaults_to_5_and_can_widen(api, runs):
    run, _ = runs

    assert api.get(f"/api/v1/metrics/throughput?run_id={run.id}").json()["picks"] == 4
    wide = api.get(f"/api/v1/metrics/throughput?run_id={run.id}&window_minutes=60").json()
    assert (wide["picks"], wide["picks_per_min"]) == (6, 0.1)


def test_run_with_no_picks_is_zero(api, db):
    run = SimRun(seed=3)
    db.add(run)
    db.commit()

    body = api.get(f"/api/v1/metrics/throughput?run_id={run.id}").json()

    assert (body["picks"], body["picks_per_min"]) == (0, 0.0)


def test_unknown_run_is_404(api, db):
    response = api.get("/api/v1/metrics/throughput?run_id=999")

    assert response.status_code == 404
    assert response.json()["code"] == "run_not_found"


@pytest.mark.parametrize(
    "query",
    ["", "run_id=0", "run_id=abc", "run_id=1&window_minutes=0", "run_id=1&window_minutes=1441", "run_id=1&window_minutes=2.5"],
)
def test_invalid_params_are_422(api, db, query):
    response = api.get(f"/api/v1/metrics/throughput?{query}")

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"

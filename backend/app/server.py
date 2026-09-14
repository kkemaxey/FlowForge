"""FlowForge API server.

Entry point for the FastAPI backend. Run with:

    uvicorn app.server:app --reload --port 8000

(from the backend/ directory, with the virtual environment active).
"""

from fastapi import FastAPI

app = FastAPI(title="FlowForge Server")


# Hard-coded for now -- this becomes a MySQL-backed `workers` table once the
# database milestone lands. Shape matches the workforce management feature
# in the design doc: human pickers and robots on the warehouse floor.
workers = [
    {
        "id": 1,
        "name": "Worker 1",
        "type": "human",
        "speed": 2,
        "cur_x": 3,
        "cur_y": 2,
        "status": "idle",
        "enabled": True,
    },
    {
        "id": 2,
        "name": "Robot 1",
        "type": "robot",
        "speed": 4,
        "cur_x": 15,
        "cur_y": 9,
        "status": "idle",
        "enabled": True,
    },
]


@app.get("/")
def read_root():
    """Basic liveness check for the API."""
    return {"status": "ok", "service": "FlowForge API"}


@app.get("/api/workers")
def get_workers():
    """Return the current roster of workers and robots on the floor."""
    return workers

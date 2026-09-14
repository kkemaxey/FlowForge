"""FlowForge checkpoint API.

A minimal FastAPI server exposing a single read-only endpoint that returns a
hard-coded list of warehouse workers (humans and robots). No database, auth,
or frontend — just enough to demonstrate a working, documented API.
"""

from fastapi import FastAPI

app = FastAPI(title="FlowForge Checkpoint API", version="0.1.0")

# Hard-coded sample data. In a later checkpoint this will come from a database.
WORKERS = [
    {
        "id": 1,
        "name": "Alice Nguyen",
        "type": "human",
        "speed": 1.4,
        "cur_x": 12,
        "cur_y": 5,
        "status": "busy",
        "enabled": True,
    },
    {
        "id": 2,
        "name": "Rover-7",
        "type": "robot",
        "speed": 3.2,
        "cur_x": 0,
        "cur_y": 0,
        "status": "idle",
        "enabled": True,
    },
    {
        "id": 3,
        "name": "Hauler-12",
        "type": "robot",
        "speed": 2.5,
        "cur_x": 34,
        "cur_y": 18,
        "status": "busy",
        "enabled": False,
    },
]


@app.get("/api/workers")
def list_workers():
    """Return the full list of warehouse workers and robots."""
    return WORKERS

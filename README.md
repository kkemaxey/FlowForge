# FlowForge

Warehouse Execution Control Tower. This repository contains the FastAPI
backend for the warehouse operations API. The Next.js frontend lives in
[`frontend/`](frontend/) and is not required to run the backend.

## Backend

Requires Python 3.11 or newer. From the repository root, create and activate
a virtual environment, then install the backend dependencies:

```bash
cd backend
python3 -m venv .venv
```

Activate the virtual environment:

```bash
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 -m uvicorn app.server:app --reload --host 127.0.0.1 --port 8000
```

The database URL can be set with `DATABASE_URL`. Without it, the backend uses
`sqlite:///./app.db` for local development.

## Workers API

List workers with `GET /api/workers` or create one with `POST /api/workers`:

```bash
curl http://127.0.0.1:8000/api/workers

curl -X POST http://127.0.0.1:8000/api/workers \
  -H 'Content-Type: application/json' \
  -d '{"name":"Packing Bot","type":"robot","speed":5,"cur_x":1,"cur_y":4}'
```

FastAPI's interactive documentation is available at http://127.0.0.1:8000/docs.

Run the backend tests from the repository root:

```bash
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
```

Example response:

```json
[
  {
    "id": 1,
    "name": "Worker 1",
    "type": "human",
    "speed": 2,
    "cur_x": 3,
    "cur_y": 2,
    "status": "idle",
    "enabled": true
  },
  {
    "id": 2,
    "name": "Robot 1",
    "type": "robot",
    "speed": 4,
    "cur_x": 15,
    "cur_y": 9,
    "status": "idle",
    "enabled": true
  }
]
```

The default worker roster is seeded when the database is empty. `GET /` is a
basic liveness check. Release changes are recorded in [`CHANGELOG.md`](CHANGELOG.md).

# FlowForge

Warehouse Execution Control Tower. This repository currently holds the
FastAPI backend for the "running server with one endpoint" assignment; the
Next.js frontend lives alongside it in [`frontend/`](frontend/) and is
not required to run the backend below.

## Backend: FastAPI server

### Prerequisites

- Python 3.11 or newer (verify with `python --version`)
- `pip` and Python's built-in `venv` module (both ship with Python)

No other tools need to be installed ahead of time.

### Install

From the repository root:

```bash
cd backend
python -m venv .venv
```

Activate the virtual environment:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (Git Bash)
source .venv/Scripts/activate
```

Then install dependencies:

```bash
pip install -r requirements.txt
```

### Run

With the virtual environment active and your working directory at
`backend/`:

```bash
uvicorn app.server:app --port 8000
```

The server listens on **http://127.0.0.1:8000**.

### Example request

```bash
curl http://127.0.0.1:8000/api/workers
```

Response:

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

This is the workforce roster the operations console will eventually render
live (see the FlowForge design doc's "Workforce management" requirement) —
hard-coded for now, backed by MySQL later in the semester.

You can also open http://127.0.0.1:8000/docs for FastAPI's interactive
Swagger UI, or hit `GET /` for a basic liveness check.

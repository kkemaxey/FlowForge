# FlowForge Checkpoint API

A standalone FastAPI server for the individual checkpoint. 
It exposes a single read-only endpoint, `GET /api/workers`, which
returns a hard-coded list of warehouse workers and robots — the workforce
roster the FlowForge operations console will eventually render live. It is
hard-coded for now and will be backed by a database later in the semester.

No database, authentication, or frontend is required to run the server below.

## Prerequisites

- macOS
- Python 3.14 (developed and tested on Python 3.14.6 — verify with the command below)
- `pip` and Python's built-in `venv` module (both ship with Python)

No other tools need to be installed ahead of time.

Verify your Python version:

```bash
python3 --version
```

## Project Structure

```text
flowforge-checkpoint/
├── app/
│   ├── __init__.py
│   └── main.py          # FastAPI app + the /api/workers endpoint
├── requirements.txt     # pinned dependencies
├── README.md
└── .gitignore
```

## Install

From the repository root (`flowforge-checkpoint/`):

```bash
python3 -m venv .venv
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

## Run

With the virtual environment active and your working directory at the
repository root:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The server listens on **http://127.0.0.1:8000**. Leave this running; stop it
with `Ctrl+C`.

## Example request

In a second terminal:

```bash
curl http://127.0.0.1:8000/api/workers
```

Response:

```json
[
  {
    "id": 1,
    "name": "Alice Nguyen",
    "type": "human",
    "speed": 1.4,
    "cur_x": 12,
    "cur_y": 5,
    "status": "busy",
    "enabled": true
  },
  {
    "id": 2,
    "name": "Rover-7",
    "type": "robot",
    "speed": 3.2,
    "cur_x": 0,
    "cur_y": 0,
    "status": "idle",
    "enabled": true
  },
  {
    "id": 3,
    "name": "Hauler-12",
    "type": "robot",
    "speed": 2.5,
    "cur_x": 34,
    "cur_y": 18,
    "status": "busy",
    "enabled": false
  }
]
```

For a formatted view, pipe the response through Python's JSON tool:

```bash
curl -s http://127.0.0.1:8000/api/workers | python3 -m json.tool
```

You can also open http://127.0.0.1:8000/docs for FastAPI's interactive
Swagger UI, which lists the endpoint and lets you try it from the browser.

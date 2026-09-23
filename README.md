# FlowForge Server

Warehouse Execution Control Tower. This repository currently holds the
FastAPI backend for the warehouse operations API; the
Next.js frontend lives alongside it in [`frontend/`](frontend/) and is
not required to run the backend below.

This server currently provides a GET endpoint that returns hard-coded warehouse worker and robot data.

## Prerequisites

- macOS
- Python 3
- Git
- Internet connection for installing Python packages

## Project Structure

```text
flowforge-server/
├── app/
│   ├── __init__.py
│   └── main.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Installation
Clone the repository:

```
git clone YOUR_REPOSITORY_URL
```

Move into the repository:

```
cd YOUR_REPOSITORY_FOLDER
```

Create a virtual environment:

```
python3 -m venv .venv
```

Activate the virtual environment:

```
source .venv/bin/activate
```

Install the required packages:

```
python3 -m pip install -r requirements.txt
```

The backend reads its database connection from the `DATABASE_URL` environment
variable. If it is not set, it uses the local SQLite database
`sqlite:///./app.db` for development.

### Run

```
python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The server will run at:

```
http://127.0.0.1:8000
```

Keep the Terminal window running while using the server.

To stop the server, press:

```
Control + C
```

## API Endpoint

### Get Workers
Method:

```
GET
```

Endpoint:

```
/api/workers
```

Full URL:

```
http://127.0.0.1:8000/api/workers
```

### Request Using curl
Run this command in another Terminal window:

```
curl http://127.0.0.1:8000/api/workers
```

### Example Response

```
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
  },
  {
    "id": 3,
    "name": "Worker 2",
    "type": "human",
    "speed": 3,
    "cur_x": 7,
    "cur_y": 5,
    "status": "busy",
    "enabled": true
  }
]
```

Workers can be created through the write endpoint:

```bash
curl -X POST http://127.0.0.1:8000/api/workers \
  -H 'Content-Type: application/json' \
  -d '{"name":"Packing Bot","type":"robot","speed":5,"cur_x":1,"cur_y":4}'
```

The service layer owns worker persistence and default seeding. Run the unit
and integration tests with coverage from `backend/`:

```bash
python -m pytest --cov=app --cov-report=term-missing -q
```

The current application version is `1.0.0`; release changes are recorded in
[`CHANGELOG.md`](CHANGELOG.md) and the GitVersion configuration is in
[`GitVersion.yaml`](GitVersion.yaml).

## Interactive API Documentation
FastAPI automatically provides interactive documentation at:

```
http://127.0.0.1:8000/docs
```
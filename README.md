# FlowForge — Pick Tasks & Live Board API (`jayden_work`)

FlowForge is a warehouse control tower for CSC 480. This branch is the backend slice behind the
supervisor's **live board**: order intake that generates pick tasks, the task lifecycle, and a
board endpoint that groups tasks by status and reports WIP, late orders and throughput. Tables
follow the course data model (`orders`, `order_lines`, `tasks`, `assignments`) in MySQL.

- Version: see [`GitVersion.yaml`](GitVersion.yaml) · changes: [`CHANGELOG.md`](CHANGELOG.md)
- Design doc (MVP, stack, API contract, features): [`docs/DESIGN.md`](docs/DESIGN.md)

## Prerequisites

- Python 3.11+ (developed on 3.14.6)
- Docker Desktop (for the local MySQL database)

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example .env        # then replace every "replace-me" value
```

Start MySQL (from the repository root):

```bash
docker compose up -d
```

## Run

From `backend/` with the virtual environment active:

```bash
uvicorn app.main:create_app --factory --port 8000
```

- Health check: http://127.0.0.1:8000/health → `{"status":"ok","version":"0.3.0","database":"connected"}`
- Swagger UI: http://127.0.0.1:8000/docs

Quick demo:

```bash
curl -X POST localhost:8000/api/orders -H 'Content-Type: application/json' \
  -d '{"due_at":"2030-01-01T12:00:00Z","lines":[{"sku_id":"SKU-88213","qty":4,"location_id":"A1-01"}]}'
curl -X PATCH localhost:8000/api/tasks/1/status -H 'Content-Type: application/json' \
  -d '{"status":"assigned","worker_id":2}'
curl localhost:8000/api/board
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/orders` | Take in an order; generates one task per line |
| GET | `/api/orders/{id}` | Get an order and its tasks |
| POST | `/api/orders/{id}/expedite` | Expedite an order |
| GET | `/api/tasks` | List tasks (`?status=open`) |
| GET | `/api/tasks/{id}` | Get one task |
| PATCH | `/api/tasks/{id}/status` | Move a task through its lifecycle |
| GET | `/api/board` | Live supervisor board |
| GET | `/health` | Version and database status |

## Tests

```bash
pytest                                  # all tests (integration tests use a temp SQLite DB)
pytest tests/unit --cov=app/modules     # business layer only, with coverage
```

To run the integration tests against MySQL, create a database whose name contains `test` and
set `TEST_DATABASE_URL` (see `.env.example`). The tests refuse to run against any other
database because they drop their tables afterwards.

## Project layout

```text
backend/
  app/core/            settings, database, request logging, errors, version
  app/modules/orders/  task and order rules, service, board builder, repository, router
  tests/unit/          business-layer tests (no database)
  tests/integration/   API tests through the real app and database
docs/DESIGN.md         design doc
GitVersion.yaml        application version
CHANGELOG.md
docker-compose.yml     local MySQL 8.4
```

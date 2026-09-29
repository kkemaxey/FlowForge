# FlowForge — Workforce API (`jayden_work`)

FlowForge is a warehouse control tower for CSC 480. This branch is a small backend slice for
the workforce: add a human or robot worker, and list everyone on the floor. Workers are stored in
the course data model's `workers` table in MySQL. The team's Next.js scaffold lives in
[`frontend/`](frontend/) and isn't needed to run the backend.

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

- Health check: http://127.0.0.1:8000/health → `{"status":"ok","version":"0.4.0","database":"connected"}`
- Swagger UI: http://127.0.0.1:8000/docs

Quick demo:

```bash
curl -X POST localhost:8000/api/workers -H 'Content-Type: application/json' \
  -d '{"name":"Maria Lopez","type":"human","speed":1.2,"cur_x":3,"cur_y":5}'
curl -X POST localhost:8000/api/workers -H 'Content-Type: application/json' \
  -d '{"name":"PickBot-7","type":"robot","speed":3.5}'
curl localhost:8000/api/workers
curl 'localhost:8000/api/workers?type=robot'
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/api/workers` | Add a worker (201; 409 duplicate name; 422 invalid input) |
| GET | `/api/workers` | List workers (`?type=robot`, `?status=idle`) |
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
  app/core/             settings, database, request logging, errors, version
  app/modules/workforce/ worker rules, service, repository, router
  tests/unit/           business-layer tests (no database)
  tests/integration/    API tests through the real app and database
docs/DESIGN.md         design doc
GitVersion.yaml        application version
CHANGELOG.md
docker-compose.yml     local MySQL 8.4
```

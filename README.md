# FlowForge — Mid-term Checkpoint: Workforce API (`jayden_work`)

FlowForge is a warehouse control tower for CSC 480. This branch is my mid-term checkpoint: a
small backend slice for the workforce: add a human or robot worker, and list everyone on the floor. Workers are stored in
the course data model's `workers` table in MySQL. The team's Next.js scaffold lives in
[`frontend/`](frontend/) and isn't needed to run the backend.

- Version: see [`GitVersion.yaml`](GitVersion.yaml) · changes: [`CHANGELOG.md`](CHANGELOG.md)
- Design doc (MVP, stack, API contract, features): [`docs/DESIGN.md`](docs/DESIGN.md)
- Presenting it? Jump to [Mid-term checkpoint demo](#mid-term-checkpoint-demo)

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

Try the endpoints with curl:

```bash
curl -X POST localhost:8000/api/workers -H 'Content-Type: application/json' \
  -d '{"name":"Maria Lopez","type":"human","speed":1.2,"cur_x":3,"cur_y":5}'
curl localhost:8000/api/workers
```

For the step-by-step presentation, see [Mid-term checkpoint demo](#mid-term-checkpoint-demo).

## Mid-term checkpoint demo

About 5 minutes, run from the Swagger page. For each step: open the endpoint, click
**Try it out**, paste the body, click **Execute**.

### Before you present

1. Start Docker Desktop and wait until it says it's running.
2. From the repository root, reset the database so worker ids start at 1:

   ```bash
   docker compose down -v
   docker compose up -d
   ```

3. Wait about 20 seconds for MySQL, then start the server from `backend/` and keep that
   terminal visible (the request log shows there):

   ```bash
   cd backend
   .venv/bin/uvicorn app.main:create_app --factory
   ```

   It is ready when it prints `Application startup complete`.
4. Open http://127.0.0.1:8000/docs. You should see a **workers** and a **health** section.

### 1. The API is up and connected

| Step | Endpoint | Body / parameters | Expected |
|---|---|---|---|
| 1 | `GET /health` | — | `200`, `"version": "0.4.0"`, `"database": "connected"` |
| 2 | `GET /api/workers` | — | `200`, `[]`: the floor is empty |

### 2. `POST /api/workers`: add workers

| Step | Body | Expected |
|---|---|---|
| 3 | `{"name": "Maria Lopez", "type": "human", "speed": 1.2, "cur_x": 3, "cur_y": 5}` | `201`, `id: 1`, `status: "idle"`, `enabled: true` |
| 4 | `{"name": "PickBot-7", "type": "robot", "speed": 3.5}` | `201`, `id: 2`, placed at the dock `(0, 0)` by default |
| 5 | `{"name": "Dev Patel", "type": "human", "speed": 1.0, "cur_x": 10, "cur_y": 4, "status": "busy"}` | `201`, `id: 3`, `status: "busy"` |

### 3. `GET /api/workers`: see who is on the floor

| Step | Parameters | Expected |
|---|---|---|
| 6 | none | `200`, all three workers in the order they were added |
| 7 | `type` = `robot` | only PickBot-7 |
| 8 | `status` = `busy` | only Dev Patel |

### 4. Bad requests are rejected (`POST /api/workers`)

| Step | Body | Expected | Why |
|---|---|---|---|
| 9 | `{"name": "maria lopez", "type": "human", "speed": 1.0}` | `409 conflict` | Names are unique, ignoring case |
| 10 | `{"name": "Speedy", "type": "human", "speed": 3}` | `422`, "speed for a human worker can be at most 2.0." | Business rule in the service layer |
| 11 | `{"name": "Drone-1", "type": "drone", "speed": 1, "cur_x": 25}` | `422` naming `body.type` and `body.cur_x` | Field validation; the grid is 20 × 12 |

Run `GET /api/workers` once more: still three workers, so nothing bad was saved.

### 5. Proof it's in MySQL and logged

12. In a second terminal (the **+** in VS Code's terminal panel), from the repository root:

    ```bash
    docker compose exec mysql sh -c 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SELECT * FROM workers"'
    ```

    The three rows print from the `workers` table (ignore the password warning).
13. Point at the server terminal: each request has an `incoming …` and a `finished … status=…`
    line with the same `request_id`, plus `worker created id=… type=…` from the service.
14. Optional: from `backend/`, run `.venv/bin/pytest -q` to show the tests passing.

### If something goes wrong

- **`/health` says `unreachable`:** MySQL isn't ready yet. Wait 20 seconds and try again.
- **`no such file or directory: .venv/bin/uvicorn`:** you're not in `backend/`. Run `cd backend` first.
- **`address already in use`:** a server is already running. Stop it with Ctrl+C in its terminal.
- **Ids don't start at 1, or step 3 returns 409:** the reset in "Before you present" was skipped.
- **Swagger page is blank:** check the address ends in `/docs`, then hard refresh (Cmd+Shift+R).

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

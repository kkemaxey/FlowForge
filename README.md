# FlowForge

Warehouse Execution Control Tower. This repository holds the FastAPI backend
in [`backend/`](backend/); the Next.js frontend lives alongside it in
[`frontend/`](frontend/) and is not required to run the backend below.

The backend provides a MySQL-backed workforce CRUD API and an events → metrics API.

## Prerequisites

- macOS, or Windows 10/11
- Python 3.11 or newer
  - **Windows:** install from <https://www.python.org/downloads/> and check
    **"Add python.exe to PATH"** on the first installer screen.
- Git
- Docker Desktop (optional — only needed to run the API with MySQL)
- Internet connection for installing Python packages

Commands below are given for both platforms. On macOS use **Terminal**; on
Windows use **PowerShell**.

Verify you have what you need:

**macOS**

```bash
python3 --version
git --version
```

**Windows (PowerShell)**

```powershell
python --version
git --version
```

## Setup

Clone the repository and move into it. The server lives on the `trentg`
branch, so check that branch out as part of the clone:

```bash
git clone -b trentg https://github.com/kkemaxey/FlowForge.git
cd FlowForge
```

Confirm you have the right files. You should see `backend`, `frontend`,
`README.md`, and `docker-compose.yml`:

```bash
ls
```

All backend commands run from the `backend/` directory:

```bash
cd backend
```

Create and activate a virtual environment (it lives at `backend/.venv`):

**macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

The `Set-ExecutionPolicy` line only affects the current PowerShell window; it
allows the activation script to run. (Git Bash on Windows:
`source .venv/Scripts/activate`.)

Your prompt should now start with `(.venv)`.

Install the dependencies (same command on both platforms):

```bash
pip install -r requirements-dev.txt
```

Create your local environment file at the repository root and edit the
passwords in it (from `backend/`):

```bash
cp ../.env.example ../.env
```

On Windows PowerShell use `Copy-Item ..\.env.example ..\.env`. The app finds
the root `.env` automatically when run from `backend/`. `.env` is gitignored —
never commit it.

## Project Structure

```text
backend/
  app/
    main.py                create_app() factory
    core/                  shared plumbing
      config.py            settings from environment variables
      database.py          engine, declarative Base, per-request session
      error_handlers.py    JSON error envelope
      exceptions.py        DomainError hierarchy
      request_logging.py   request logging with X-Request-ID
      health.py            GET /health
      version.py           reads GitVersion.yaml
      clock.py             UTC clock
    modules/
      workforce/           workers: router, schema, service, repository, models,
                           assigner, task state machine
      metrics/             events and metrics: router, schema, service,
                           repository, models
      orders/              (team scaffold)
  scripts/                 seed_workers.py, demo_events.py
  tests/unit/              business-layer tests (no database)
  tests/integration/       API tests through FastAPI's TestClient
  Dockerfile               API image (built from the repository root)
  requirements.txt         runtime dependencies
  requirements-dev.txt     runtime + test dependencies
frontend/                  Next.js operations console (not needed for the backend)
docs/API.md                endpoint reference
docker-compose.yml         API + MySQL stack
GitVersion.yaml            application version
CHANGELOG.md               release notes
```

Business logic (`modules/*/service.py`, `assigner.py`, `task_states.py`,
`core/exceptions.py`, `core/clock.py`) does not import FastAPI or SQLAlchemy.

## Running with Docker (API + MySQL)

From the repository root:

```bash
docker compose up --build
docker compose exec api python -m scripts.seed_workers
```

## Running without Docker

For a quick start with no MySQL, set `DATABASE_URL=sqlite:///./flowforge.db` in `.env`, then from `backend/`:

```bash
uvicorn app.main:create_app --factory --reload
python -m scripts.seed_workers
```

### Google Cloud SQL

To run against the team's Cloud SQL (MySQL) instance, start the
[Cloud SQL Auth Proxy](https://cloud.google.com/sql/docs/mysql/sql-proxy) in a
separate terminal:

```bash
cloud-sql-proxy senior-capstone-508523:us-east4:free-trial-first-project --port 3306
```

Then set `DATABASE_URL` in `.env` to the Cloud SQL user and database through
the proxy, e.g. `mysql+pymysql://<user>:<password>@127.0.0.1:3306/<database>`,
and start uvicorn from `backend/` as above.

The proxy and the Compose `db` service both use port 3306, so only one of them
can run at a time.

## Trying it out

- Interactive docs: <http://127.0.0.1:8000/docs>
- Health: `curl http://127.0.0.1:8000/health` (Windows: `curl.exe`)
- Generate demo traffic (from `backend/`): `python scripts/demo_events.py`

Type `curl.exe`, not `curl`, in Windows PowerShell — there, plain `curl` is a different command
that prints a formatted object instead of the raw JSON.

See [docs/API.md](docs/API.md) for every endpoint, status code, and error code.

## Running Tests

From `backend/`:

```bash
pytest
pytest --cov=app --cov-report=term-missing
```

To run the integration tests against MySQL instead of in-memory SQLite, set
`TEST_DATABASE_URL` to a MySQL URL first.

## Versioning

The version lives in `GitVersion.yaml` (`next-version`) and is reported by `/health`.
Every change is recorded in `CHANGELOG.md`.

## Stopping the Server

Press `CTRL+C` in the terminal running uvicorn, then deactivate the
virtual environment:

```bash
deactivate
```

If you started the Docker stack, stop it from the repository root with:

```bash
docker compose down
```

`docker compose down -v` also deletes the MySQL data volume, so the next start
begins with an empty database (re-run the seed script).

## Troubleshooting

**`command not found: uvicorn`** (macOS) or **`uvicorn : The term 'uvicorn' is not
recognized`** (Windows) — the virtual environment is not active. From `backend/`,
run `source .venv/bin/activate` (macOS) or
`.venv\Scripts\Activate.ps1` (Windows) and try again.

**`running scripts is disabled on this system`** (Windows) — run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that same
PowerShell window, then activate again.

**`Python was not found; run without arguments to install from the Microsoft
Store`** (Windows) — Python is not on your PATH. Re-run the python.org installer,
choose **Modify**, and enable **"Add Python to environment variables"**, then
open a new PowerShell window.

**`Error loading ASGI app. Could not import module "app.main".`** — you are not
in `backend/`. `cd backend` (the directory containing `requirements.txt`), then run
`uvicorn app.main:create_app --factory --reload`.

**`[Errno 48] Address already in use`** (macOS) or **`[WinError 10048]`**
(Windows) — port 8000 is taken. Start on a
different port and use it in your `curl`:

```bash
uvicorn app.main:create_app --factory --reload --port 8001
```

**`RuntimeError: DATABASE_URL is not set`** — create `.env` at the repository root from `.env.example` (see Setup).

**`{"error":{"code":"not_found",...}}`** — check the URL. The path is `/api/workers`, not `/workers`.

# Changelog

All notable changes to FlowForge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Simulation, exception handling, the event log and metrics (Kendyn), plus the
first database tables and synthetic demo data. Branch `feature/simulation`.

### Added

- First real database schema: migration `0002_core_warehouse_tables` creates
  `locations`, `skus`, `inventory`, `workers`, `orders`, `order_lines`,
  `tasks`, `assignments`, `users`, `sim_runs`, `exceptions` and `events`.
  Timestamps are `DATETIME(3)` on MySQL and stored as UTC. Status tables carry
  a `version` column for compare-and-set updates; `assignments` is append-only.
- Draft models in teammates' modules, each marked for its owner's review:
  `orders/models.py` and `tasks/models.py` and `assignment/models.py` (Kanayo),
  `workforce/models.py` (Trent), `auth/models.py` (Brock).
- `simulation/models.py`: `Location`, `Sku`, `Inventory` (on_hand/reserved per
  bin), `SimRun` and `TaskException`. Simulation now owns inventory and the map.
- `events/models.py` and `events/service.py`: `record_event()` writes an event
  inside the caller's transaction and stamps the active run. Event types:
  `order_received`, `task_created`, `task_assigned`, `task_picked`,
  `task_rerouted`, `task_exception`, `task_reopened`, `order_completed`,
  `exception_opened`, `worker_status_changed`.
- `POST /api/v1/tasks/{task_id}/exceptions` (`stockout`, `jam`, `worker_down`).
  It works in one transaction: records the exception, closes the assignment as
  `failed`, updates the worker, and reroutes the task to the nearest other bin
  with enough unreserved stock, releasing and reserving inventory to match.
  - Stockout sets the bin's `on_hand` to `qty_found`.
  - If no bin has stock, the task goes to `exception` and waits for the
    supervisor.
  - On `worker_down`, the worker goes `down` and the task reopens in place.
  - Exceptions the system handles itself are saved already resolved.
  - Returns 404 for an unknown task or assignment, 409 when the state has
    moved on or the version check fails, and 422 for bad input.
- `GET /api/v1/exceptions?open=true|false`: unresolved (supervisor queue) or
  resolved exceptions, newest first; all when `open` is omitted.
- `POST /api/v1/tasks/{task_id}/pick`: completes a pick (takes stock out of the
  bin, closes the assignment, frees the worker at the bin). When an order's
  last task is picked, the order and its tasks move to `complete`.
- `GET /api/v1/metrics/throughput?run_id=&window_minutes=`: `task_picked`
  events for a run in the window, as `picks` and `picks_per_min`.
- Simulator support endpoints: `GET /api/v1/simulation/runs/active`,
  `POST /api/v1/simulation/runs`, `GET /api/v1/simulation/assignments/active`,
  `POST /api/v1/simulation/workers/{id}/recover` and
  `GET /api/v1/inventory/skus`.
- Demo tooling, run from `backend/` as
  `python -m app.modules.simulation.cli <command>`:
  - `seed`: synthetic warehouse built through the models, with a fixed default
    seed (480):
    - One warehouse on a 10x10 grid: 45 locations (42 bins and 3 pick/pack
      stations), with zones and aisles.
    - 25 SKUs, one SKU per bin, about half of them in 2-3 bins, and 3
      deliberately low-stock.
    - 5 workers and 5 robots.
    - A simulation run.
    - Optional supervisor and simulator Firebase logins, from env vars.
    - Sizes can be set with flags or `SEED_*` env vars.
    - Re-running without `--reset` does nothing; `--reset` refuses
      non-SQLite databases unless `FLOWFORGE_ALLOW_RESET=1`.
  - `run`: the worker/robot simulator.
    - Runs as a separate process and only goes through the API, signed in as
      the `SIM_EMAIL` Firebase user (no auth bypass).
    - Travel time is Manhattan distance / speed, plus the pick time.
    - Exception probabilities, tick rate and worker speed come from flags or
      `SIM_*` env vars; a seed makes runs repeatable.
    - Downed workers recover after `--recovery-seconds`.
  - `orders`: posts orders to `POST /api/v1/orders` at a set rate, using only
    SKUs with stock, 1-4 lines each and a unique `external_ref`.
  - `trigger`: raises a stockout, jam or worker_down on a task right away, for
    live demos.
  - `demo`: offline end-to-end run on a local `demo.db` (no server, no
    Firebase) that prints throughput and exceptions.
- `core/errors.py`: `ApiError` and handlers so every error body is
  `{"detail": "...", "code": "..."}`, including validation errors.
- `core/database.py`: shared `Timestamp` column type and `utcnow()`.
- Tests: `tests/sim_fixtures.py` (shared in-memory DB and an authed client)
  and test modules for events, seed, exceptions, the exceptions list, picks,
  throughput, the simulator (including an end-to-end order) and the order
  generator. 70 tests in total.
- Frontend types for exceptions and throughput, the `exception` task status
  and the `down` worker status in `frontend/types/index.ts`.
- New env vars documented in `backend/.env.example`.

### Changed

- **All module routes now live under `/api/v1`** (`main.py` adds the prefix
  when including routers). `/health` is unchanged.
- The `events` router no longer uses an `/events` prefix; its endpoint is
  `/api/v1/metrics/throughput`.

### Known issues

- Order intake, task generation and the greedy assigner (Kanayo) don't exist
  yet. Until they do, `cli orders` gets 404s and `cli run` has nothing to
  pick. `simulation/demo.py` has temporary stand-ins for both, used by the
  demo and tests; remove them once the real ones land. Intake and the assigner
  also need to call `record_event()` for `order_received`, `task_created` and
  `task_assigned`.
- The order payload `{external_ref, lines: [{sku_code, qty}]}` is assumed and
  needs to match Kanayo's intake schema.
- A jammed bin isn't blocked afterwards, so a task can be rerouted straight
  back to it.
- No endpoint resolves an exception yet; tasks in `exception` stay there.
- Tested on SQLite only; row locks and `DATETIME(3)` haven't been run against
  MySQL. Firebase sign-in for the simulator hasn't been tried with real
  credentials.

## [0.2.0] - 2026-09-30

Sprint 0 foundation filled in: a runnable backend and frontend skeleton, CI
and deploy files.

### Added

- Backend modules `tasks`, `assignment`, `simulation`, `workforce`, `auth` and
  `events`, each with `router.py`, `models.py`, `schemas.py` and `service.py`,
  and an empty `APIRouter` per module.
- `backend/app/main.py` app factory with CORS, a `GET /health` endpoint and
  every module's router registered.
- `core/config.py` (settings from environment variables and `backend/.env`),
  `core/database.py` (shared SQLAlchemy `Base`, engine and `get_db`) and
  `core/security.py` (`get_current_user` Firebase ID-token check).
- Alembic setup: `alembic.ini`, `alembic/env.py` loading every module's models,
  and an empty `0001_initial` baseline migration.
- Backend pytest setup (`tests/conftest.py`) and a `/health` test.
- `backend/Dockerfile` and `.dockerignore` for Cloud Run.
- `backend/.env.example` and `frontend/.env.example`.
- Frontend supervisor login page (`app/(auth)/login`) using Firebase
  email/password sign-in.
- Console shell (`app/console/`) with a sign-in gate that redirects to `/login`,
  and placeholder panels in `grid-map/`, `controls/`, `live-board/` and
  `workforce/`.
- `lib/firebase.ts` (lazy Firebase init), `lib/api-client.ts` (`apiFetch` that
  attaches the Firebase token, and `getHealth`), `components/ui/Card.tsx` and
  `types/index.ts`.
- GitHub Actions CI (`.github/workflows/ci.yml`): backend pytest, frontend lint
  and build.
- `ARCHITECTURE.md` explaining ownership, the module pattern and how modules
  connect.
- Root `.gitignore`.

### Changed

- `README.md` rewritten: project overview, status, scope, stack, team, layout,
  setup, environment variables, contributing and deployment.
- `CODEOWNERS` now covers `controls/`, the workforce frontend, `events/`, the
  login page, the shared core, `main.py`, `api-client.ts`, the Dockerfile and CI.
- `backend/requirements.txt` adds SQLAlchemy, Alembic, PyMySQL, cryptography,
  firebase-admin, python-dotenv, pytest and httpx.
- Frontend home page now shows the backend's `/health` status and links to the
  console; page title is "FlowForge".
- `frontend/.gitignore` allows `.env.example` to be committed.

### Removed

- Unused Next.js template SVGs in `frontend/public/`.

### Fixed

- Renamed `modules/orders/schema.py` to `schemas.py` to match the module
  convention.

### Known issues

- Not yet run locally or in CI; the backend tests and frontend build are
  untested.
- Nothing is deployed, and Firebase and Cloud SQL are not set up.

## [0.1.0] - 2026-09-17

Sprint 0 foundation: monorepo skeleton in the feature-folder layout.

### Added

- Backend feature-folder skeleton under `backend/app/`:
  - `main.py` app entry point
  - `core/config.py`, `core/database.py`, `core/security.py`
  - `modules/orders/` with `models.py`, `router.py`, `schema.py`, `service.py`
- Frontend shared library stubs: `frontend/lib/api-client.ts` and `frontend/lib/firebase.ts`.
- `.github/CODEOWNERS` mapping backend modules (orders, tasks, assignment,
  simulation, workforce, auth) and frontend console folders (grid-map,
  live-board) to their owners.
- Next.js (App Router) + TypeScript frontend boilerplate in `frontend/`, with
  Tailwind CSS, ESLint and the `firebase` SDK as dependencies.

### Removed

- `backend/app/server.py`, the single-file FastAPI server with a hard-coded
  `GET /api/workers` roster, superseded by the feature-folder layout.

### Known issues

- All scaffold files in `backend/app/` and `frontend/lib/` are empty
  placeholders; the backend does not start yet.
- `README.md` still documents `uvicorn app.server:app` and `GET /api/workers`,
  which no longer exist.
- `backend/app/modules/orders/schema.py` should be `schemas.py` to match the
  module convention.
- Module folders for tasks, assignment, simulation, workforce, auth and events,
  and the frontend `console/` and `(auth)/login` folders, are not created yet.
- `CODEOWNERS` has no entries for `frontend/app/console/controls/` or the
  workforce CRUD frontend.

## [0.0.1] - 2026-09-13

Initial "running server with one endpoint" assignment.

### Added

- FastAPI backend (`backend/app/server.py`) with:
  - `GET /` liveness check
  - `GET /api/workers` returning a hard-coded roster of workers and robots
- `backend/requirements.txt` pinning FastAPI 0.115.6 and Uvicorn 0.34.0.
- `backend/.gitignore` for virtual environments and Python caches.
- `README.md` with backend setup, run and example-request instructions.

[Unreleased]: https://github.com/kkemaxey/FlowForge/compare/48eec4c...HEAD
[0.1.0]: https://github.com/kkemaxey/FlowForge/compare/12a1a27...48eec4c
[0.0.1]: https://github.com/kkemaxey/FlowForge/commit/12a1a27

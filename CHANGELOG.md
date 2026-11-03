# Changelog

All notable changes to FlowForge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Review fixes for the live board and portal (Jayden, 2026-11-03): one
warehouse, the real `/api/v1` backend shapes, and a board that keeps working
without the metrics endpoint.

### Changed

- Portal pages moved off `/w/[id]`: the console, metrics, exceptions and order
  pages are now `/console`, `/metrics`, `/exceptions` and `/orders/[id]`, and
  the admin pages are `/admin/layout`, `/admin/inventory`, `/admin/workforce`
  and `/admin/simulation`. The side nav and the `/403` back link follow.
- The console shows the `WorkforcePanel` (Trent) and `Controls` (Aalan)
  components in place of their placeholder boxes.
- `live-board/data.ts` calls `/api/v1` and maps the backend's shapes onto the
  board's types: `{items, count}` task lists, `task_id` / `sku_code` / `qty`,
  the `location` object, `current_assignment.worker_id`, task `picked` as
  complete, and order `open` split into new, in progress or late.
- The board loads orders from `GET /api/v1/orders/{id}` for the newest order
  ids in the task list, since there is no order list endpoint yet.
- `useLiveBoard` uses `Promise.allSettled`: metrics are optional, so a missing
  metrics endpoint no longer hides orders and tasks. Task counts and WIP are
  worked out from the tasks in `boardLogic.ts`.
- API base URL defaults to `http://localhost:8080` in `lib/api-client.ts` and
  `frontend/.env.example`.
- `apiFetch` only attaches a Firebase token when Firebase is configured, so
  real-data mode works before login is set up.
- `live-board/README.md` now documents the real endpoints, the mapping and the
  gaps for the backend.

### Removed

- The warehouse picker (`/warehouses`), `/admin/warehouses/new`, the
  `?warehouse_id=` param, and the 5 × 5 and 60 × 40 test warehouses.
- The old `/console` scaffold page and its Firebase sign-in gate; the portal
  console replaces it. Sign-in is part of Brock's login work.

## [0.7.0] - 2026-11-03

Supervisor live board, warehouse grid and portal wireframes, by Jayden.
Built on mock data until the orders, tasks and events endpoints exist, then
reviewed against the course Engineering Standards (2026-10-17). Then the portal
wireframes, warehouse grid and the backend's 10 × 10 demo warehouse
(2026-11-02).

### Added

- Live board panel (`frontend/app/console/live-board/LiveBoard.tsx`): orders
  table with status badges and highlighted late orders, task counts per
  status, Throughput (units and tasks per hour) and WIP tiles, and a red
  exception banner showing the task, location and exception type.
- `useLiveBoard.ts` hook that polls `GET /orders`, `GET /tasks` and
  `GET /events/metrics` every 2 seconds, with loading and error states, and
  stops polling when the board unmounts.
- `data.ts` with `Order`, `OrderLine`, `Task` and `LiveMetrics` types and
  `getOrders()`, `getTasks()` and `getMetrics()`, which return mock data or
  call the backend through `apiFetch`.
- `mockData.ts`, an in-browser warehouse simulator (orders arriving, tasks
  moving open → assigned → picked → complete, occasional stockouts that are
  reassigned, late orders) so the board updates without a backend.
- `boardLogic.ts` holding the board's calculations (exception list, WIP total,
  order sorting) as plain functions, separate from the UI.
- `live-board/README.md` listing the exact JSON shapes the board expects from
  `GET /orders`, `GET /tasks` and `GET /events/metrics`.
- `NEXT_PUBLIC_USE_MOCKS` in `frontend/.env.example` (defaults to `true`).
- Explanatory comments throughout the live board code.
- KPI strip (Throughput, WIP, On-time) and a throughput chart on the live
  board (2026-11-02).
- `WarehouseGrid` component that draws a warehouse's cells (storage, aisle,
  station, blocked) with a legend and per-cell tooltips, plus mock warehouses
  at the smallest (5 × 5) and largest (60 × 40) allowed sizes (2026-11-02).
- Portal shell: side navigation, a mock Admin/Supervisor role toggle, and a
  redirect from `/admin` pages to `/403` for supervisors (2026-11-02).
- Wireframe pages for every portal route: login, warehouses, operations
  console, orders, exceptions, metrics, and the admin layout, inventory,
  workforce, simulation, users and new-warehouse pages (2026-11-02).
- `mocks/demoWarehouse.ts`, the 10 × 10 demo warehouse the backend seeds: pick
  stations at (3,0) and (6,0), 48 bins in aisles A1–A3 and B1–B3, 20 shoe SKUs
  stocked in 30 bins, and 5 human and 5 robot workers at their starting
  positions (2026-11-02).

### Changed

- Reviewed the live board against the Engineering Standards: moved logic out
  of the UI components into `boardLogic.ts`, and removed an unused
  `"use client"` directive from the polling hook.
- Warehouse 1 in the mocks is now the backend's 10 × 10 demo warehouse
  instead of a 20 × 12 stand-in map (2026-11-02).
- The live board simulator now picks real SKUs from stocked bins (with
  quantities no larger than the bin holds) and assigns tasks to the 10 demo
  workers (2026-11-02).
- Trimmed comments that restated the code or named an owner (2026-11-02).
- Regenerated `frontend/package-lock.json` so `npm ci` (and the frontend CI
  job) installs again (2026-11-02).

### Removed

- Unused `WorkerStatus` re-export from `live-board/data.ts` (dead code).
- `mocks/warehouse-map.json`, the 20 × 12 stand-in map (2026-11-02).

### Known issues

- The live board types live in `live-board/data.ts` until they are reviewed
  for the shared `types/index.ts`; the shared `TaskStatus` has no `exception`
  value yet.

## [0.6.0] - 2026-11-02

Supervisor overrides and the order generator, by Kanayo: reassign, expedite,
and a seeded order stream that runs inside the backend.

### Added

- `POST /api/v1/tasks/{task_id}/reassign` (`{worker_id, expected_version,
  reason?}`), in one transaction: version check through `transition()`, claim
  the idle target worker, close any previous open assignment (outcome
  `reassigned`), open a new `source=supervisor` assignment, and write
  `task_reassigned` (or `task_assigned` if there was no previous assignment).
  Also assigns `open` and `exception` tasks directly.
- Reassign errors: 409 `worker_unavailable` when the target isn't idle and
  active, and 409 `assignment_conflict` on a unique-key race.
- `POST /api/v1/orders/{order_id}/expedite`: sets `expedited=true`, raises the
  order and its unfinished tasks to priority 110 (`EXPEDITE_PRIORITY`), and
  writes an `order_expedited` event. The order update is a compare-and-set on
  `orders.version`. Returns 409 `order_complete` / `version_conflict`, or 404;
  expediting twice is a no-op 200.
- `generator` module (`app/modules/generator/`) with `GET /api/v1/generator`,
  `POST /api/v1/generator/start` and `POST /api/v1/generator/stop`:
  - `OrderStream`: seeded random orders (1–3 shoes, 1–3 pairs each, priority 0,
    due in 30 min) at random gaps averaging `order_rate`; the same seed gives
    the same stream.
  - Each start creates a new `sim_runs` row; `stop()` sets its `ended_at`, and
    the app's shutdown calls it.
  - Orders go through the same intake code as `POST /orders`. Rejected orders
    are counted, shoes with 0 unreserved pairs are tracked as out of stock, and
    a 5 s check drops them once they are restocked.
  - Returns 409 `generator_running` / `no_skus`.
- `InsufficientStock` error (subclass of `ApiError`, carries `sku_code` and
  `available`) so the generator can tell intake rejections apart. The HTTP
  response is unchanged.
- Tests: `test_reassign.py`, `test_expedite.py` and `test_generator.py`
  (50 tests). 129 tests now pass against MySQL.

### Changed

- The small-warehouse test helper (`floor`) moved to `tests/conftest.py` so the
  assigner, reassign and expedite tests share it.
- `main.py` registers the generator router and stops the generator on shutdown.

### Known issues

- Expedite does not change who gets assigned in `greedy_v1`: a nearer normal
  task still beats a far expedited one. This is intentional for the MVP and is
  covered by a test.
- Expedite raises priority on all unfinished tasks, not only `open` ones as the
  spec says; waiting on confirmation.
- Workers stay busy after one task each until pick completion is built.

## [0.5.0] - 2026-10-29

Greedy assigner with a background loop, and one error format for every route,
by Kanayo.

### Added

- `POST /api/v1/assignments/run`: plans in memory (each idle, active worker
  takes the nearest open task by Manhattan distance, ties to the oldest task),
  then writes each pairing in its own transaction (task `open` → `assigned`,
  worker `idle` → `busy`, an assignments row with `source=scheduler`,
  `algorithm` and `score`, and a `task_assigned` event). Returns
  `{algorithm, assignments, conflicts}`, or 422 `unknown_algorithm` /
  `unknown_run`.
- `ALGORITHMS` registry in `assignment/service.py`, starting with `greedy_v1`.
- Background assigner loop (`assignment/loop.py`): one pass every
  `ASSIGNER_INTERVAL_SECONDS` (default 2) in a worker thread; logs and
  continues if a pass crashes, and stops cleanly on shutdown.
- `ASSIGNER_LOOP_ENABLED` and `ASSIGNER_INTERVAL_SECONDS` settings in
  `core/config.py`; Docker Compose turns the loop on.
- Error handlers in `core/errors.py` for framework errors, all in the
  `{detail, code}` shape: 404 `not_found`, 405 `method_not_allowed` (keeps the
  `Allow` header), 500 `internal_error`, 401 `unauthorized`, 403 `forbidden`
  and `http_error` for any other `HTTPException`.
- Tests: `test_assignment.py` (26 tests, including conflicts injected between
  the plan and write steps) and `test_errors.py` (4 tests).

### Changed

- `tests/conftest.py` forces the assigner loop off so it can't race the tests.
- `backend/.env.example` adds the assigner interval.

### Security

- 500 responses only say "Internal server error"; the full trace goes to the
  backend log, and a test checks that nothing leaks.

### Known issues

- The loop assumes a single backend instance. More instances are still safe,
  but waste passes on conflicts.

## [0.4.0] - 2026-10-21

Order intake and the task state machine, by Kanayo.

### Added

- `POST /api/v1/orders`: in one transaction, saves the order and lines, creates
  tasks (one bin if it covers the line, otherwise split across bins, largest
  unreserved stock first), raises `qty_reserved` under `SELECT ... FOR UPDATE`,
  and writes `order_received` and `task_created` events.
  - A repeated `external_ref` returns 200 with the stored order and writes
    nothing, including when two identical requests race.
  - 422 `unknown_sku` / `unknown_run`, 409 `insufficient_stock`; any failure
    rolls back every line.
  - `priority` is limited to 0–100.
- `GET /api/v1/orders/{id}`: the order with its lines, tasks and bin locations.
- `GET /api/v1/tasks?status=&limit=`: highest priority first, then oldest, then
  task id. Each item includes `current_assignment` or `null`. `limit` is 1–500,
  default 50.
- `transition()` in `tasks/service.py`: every task status change is a
  compare-and-set on `status` and `version`. Raises 409 `version_conflict`
  when another writer got there first, and 409 `invalid_transition` for moves
  outside the allowed table (`open` → `assigned` → `picked`, plus reassign,
  requeue and exception moves). It doesn't commit or write events; the caller
  does both.
- `core/errors.py`: `ApiError` and handlers so errors are `{"detail", "code"}`.
- `core/schemas.py`: `UtcDatetime`, which outputs UTC like
  `2026-10-20T14:02:11.204Z`.
- Tests: `test_orders.py` (17 tests) and `test_tasks.py` (31 tests, including a
  real two-session race and a test that pins the transition table).

### Changed

- Tests run against the `flowforge_test` MySQL database instead of SQLite.
  `conftest.py` migrates it once per run and empties it before each test;
  database tests skip when MySQL isn't available.
- `utcnow()` in `core/database.py` drops anything finer than a millisecond, so
  API timestamps match what MySQL stores.
- `LocationOut` moved to `warehouse/schemas.py` and is shared by the orders and
  tasks responses.

### Fixed

- A test helper treated `lines=[]` as "not given", so one order test passed
  when it should have failed.
- The suite took 30 s because `TRUNCATE` rebuilds each table; it now uses
  `DELETE` (and `TRUNCATE` only for `events`) and takes about 5 s.

### Known issues

- Insufficient stock at intake is still an open team decision: reject with 409
  (built now, marked `TODO(team decision)` in `_allocate`) or accept and open an
  exception.
- `count` in `GET /tasks` is the number of items returned; whether it should be
  the total matching tasks is undecided.

## [0.3.0] - 2026-10-14

Local Docker stack, the full database schema and a seeded shoe warehouse, by
Kanayo.

### Added

- `docker-compose.yml` with a `db` service (`mysql:8.0`, utf8mb4, strict SQL
  mode, UTC, a `db_data` volume and a healthcheck) and a `backend` service
  (built from `backend/Dockerfile`, code mounted with `--reload`, port 8080).
- `docker/mysql/init/01-test-database.sh`, which creates the `flowforge_test`
  database on first start.
- `warehouse` module with the `locations`, `skus` and `inventory` models.
- Base models for teammates' tables in their own modules: `workers`
  (`workforce/`), `events` (`events/`), `users` (`auth/`), and `sim_runs` and
  `exceptions` (`simulation/`).
- Migration `0002_core_schema.py` for all 12 tables, including:
  - one open assignment per task and per worker (generated columns
    `active_task_id` / `active_worker_id` with unique keys)
  - `version` columns on `tasks` and `orders` for compare-and-set
  - append-only `events` triggers (`events_no_update`, `events_no_delete`)
- Seed script `app/seed.py` (`python -m app.seed`, fixed seed 480): a 10×10
  warehouse with 48 storage bins and 2 pick stations, 20 shoe SKUs (three kept
  thin so orders split across bins), 5 humans, 5 robots, a placeholder
  supervisor and a `greedy_v1` sim run. It refuses to run if data exists.

### Changed

- `backend/.env.example` points at the Docker MySQL and the test database
  instead of SQLite / Cloud SQL.
- `alembic/env.py` imports the warehouse models.
- Order statuses are `open` / `complete` and task statuses are `open` /
  `assigned` / `picked` / `exception`, matching the spec; `travel_cost` is now
  `score` and `received_at` is now `created_at`.
- `version` starts at 0 and is only changed by explicit compare-and-set
  updates, replacing SQLAlchemy's `version_id_col`.

### Fixed

- The backend couldn't connect on MySQL's first start because the healthcheck
  passed during setup; it now pings `127.0.0.1` over TCP.
- `CREATE TRIGGER` failed with error 1419 because of binary logging; compose now
  runs MySQL with `--skip-log-bin`.

### Known issues

- The design doc, `ARCHITECTURE.md` and `SPRINT_PLAN.md` still describe Cloud
  Run and Cloud SQL.
- Auth is off; all endpoints are open for the MVP.

## [0.2.0] - 2026-09-30

Sprint 0 foundation filled in, by Kanayo: a runnable backend and frontend
skeleton, CI and deploy files.

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

Sprint 0 foundation, by Kanayo: monorepo skeleton in the feature-folder layout.

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

Initial "running server with one endpoint" assignment, by Kanayo.

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

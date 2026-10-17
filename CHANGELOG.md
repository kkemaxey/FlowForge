# Changelog

All notable changes to FlowForge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Live board for Sprint 1 and Sprint 2 (Jayden), built on mock data until the
orders, tasks and events endpoints exist, then reviewed against the course
Engineering Standards (2026-10-17).

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

### Changed

- Reviewed the live board against the Engineering Standards: moved logic out
  of the UI components into `boardLogic.ts`, and removed an unused
  `"use client"` directive from the polling hook.

### Removed

- Unused `WorkerStatus` re-export from `live-board/data.ts` (dead code).

### Known issues

- The live board types live in `live-board/data.ts` until they are reviewed
  for the shared `types/index.ts`; the shared `TaskStatus` has no `exception`
  value yet.
- `frontend/package-lock.json` is out of sync with `package.json`, so
  `npm ci` fails.

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

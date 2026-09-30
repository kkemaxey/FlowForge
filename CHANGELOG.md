# Changelog

All notable changes to FlowForge are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

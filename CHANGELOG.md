# Changelog

All notable changes to this branch are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow
[Semantic Versioning](https://semver.org/), and the newest version always matches
`next-version` in `GitVersion.yaml`.

## [Unreleased]

## [0.2.0] - 2026-09-29

Pick tasks and the live supervisor board, backed by MySQL.

### Added
- Pick-task lifecycle state machine: `open → assigned → in_progress → picked`, with
  `exception` from any active status and `assigned`/`exception → open` to return work to the pool.
- `TaskService` business layer: validates due times, requires a worker to assign and a
  reason to raise an exception, stamps completion times, and expedites tasks.
- Live-board builder: groups tasks into status columns, sorts expedited work first, flags
  late tasks, and reports WIP, exceptions and picks in the last hour.
- MySQL persistence through SQLAlchemy 2.1 (`pick_tasks` table); connection string read from
  the `DATABASE_URL` environment variable.
- Endpoints: `POST /api/tasks`, `GET /api/tasks`, `GET /api/tasks/{id}`,
  `PATCH /api/tasks/{id}/status`, `POST /api/tasks/{id}/expedite`, `GET /api/board`, `GET /health`.
- Request logging on arrival and completion, tagged with an `X-Request-ID`.
- Consistent JSON error envelope with 404, 409, 422 and 500 status codes.
- Unit tests for the state machine, service and board builder; integration tests against the API.
- `docker-compose.yml` for a local MySQL 8.4, `.env.example`, design doc and API reference.

### Changed
- Moved the server into `backend/` to match the team repository layout.
- Run command is now `uvicorn app.main:create_app --factory` from `backend/`.

### Removed
- Hard-coded worker list and `GET /api/workers` from the 0.1.0 checkpoint (workforce CRUD is
  owned by the integration role).

## [0.1.0] - 2026-09-13

### Added
- Standalone FastAPI server with `GET /api/workers` returning a hard-coded worker list.
- README with setup and run instructions.

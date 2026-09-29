# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and versions follow [Semantic Versioning](https://semver.org/) and match
`next-version` in `GitVersion.yaml`.

## [Unreleased]

## [0.1.0] - 2026-09-29

### Added
- Environment-based configuration (`DATABASE_URL`, `LOG_LEVEL`, `GRID_WIDTH`, `GRID_HEIGHT`).
- `GitVersion.yaml` as the single source of the application version.
- pytest setup with separate unit and integration suites.
- Task lifecycle state machine (open → assigned → picked, with exception and reassignment paths).
- Greedy nearest-task assigner (Manhattan distance), translated from the course baseline.
- Workforce service: grid-bounds validation, server-owned status, and no deleting busy workers.
- Metrics service: throughput per hour, units picked, exceptions, WIP, and worker status counts from the event stream.
- MySQL persistence via SQLAlchemy 2.0: `workers` and `events` tables and repositories.
- `GET /health` reporting version and database connectivity.
- Request logging (arrival and completion, with `X-Request-ID`) and a consistent JSON error envelope.
- Workforce CRUD API: `GET/POST /api/workers`, `GET/PATCH/DELETE /api/workers/{id}`.
- Events → metrics API: `POST /api/events` and `GET /api/metrics?window_minutes=`.
- Docker image and Compose stack (API + MySQL 8.0 with healthcheck); `.env.example` template.
- Demo scripts: `scripts/seed_workers.py` and `scripts/demo_events.py`.

### Removed
- Hard-coded mock worker list from the original `app/main.py`.

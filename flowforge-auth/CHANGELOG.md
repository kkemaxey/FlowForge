# Changelog

All notable changes to the FlowForge Auth Service are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com); this project uses
[Semantic Versioning](https://semver.org). The current version (0.1.0) matches
`VERSION` and `GitVersion.yaml`.

## [0.1.0] - 2026-09-28
### Added
- Firebase-backed authentication dependency, with a dev-mode token path for local demos.
- `POST /auth/login` — verifies the caller, assigns their role, upserts the user, and
  records a login event (two database writes).
- `GET /auth/me` — returns the current user and their supervisor status (database read).
- Supervisor role modeled in the business layer (`services.assign_role`, `services.is_supervisor`),
  kept out of the route handlers so it is unit-testable in isolation.
- Request-logging middleware and a `/health` liveness endpoint.
- Database integration via SQLAlchemy with credentials read from environment variables.
- Seed script (`app/seed.py`) that creates the schema and loads sample users and login events.
- Unit tests against the business layer and one integration test against the API.

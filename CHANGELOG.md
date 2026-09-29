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

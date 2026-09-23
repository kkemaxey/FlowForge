# Changelog

## [1.0.0] - 2026-09-22

- Added environment-based database configuration through `DATABASE_URL`.
- Added worker service functions for database reads, writes, seeding, and serialization.
- Added `GET /api/workers` and `POST /api/workers` integration coverage.
- Added business-layer unit tests and coverage reporting with pytest-cov.
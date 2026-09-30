# Changelog

## [1.0.0] - 2026-09-22

- Added SQLAlchemy-backed database configuration through `DATABASE_URL`, with SQLite used by default for local development.
- Added persistent worker models and service operations for listing, creation, default seeding, and response serialization.
- Added `GET /api/workers` and `POST /api/workers` endpoints with unit and integration tests.
- Added test coverage reporting with pytest-cov.
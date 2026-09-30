# FlowForge Auth Service

Authentication + supervisor-role backend slice for the FlowForge warehouse
control tower. Two integrated endpoints, a seeded database (read + write),
tests, and request logging.

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # defaults run locally on SQLite in dev mode
```

## Create the database and load sample data

```bash
python -m app.seed
```

This creates the schema and inserts sample users (a supervisor and workers) plus
some login events. Re-running it is safe.

## Run the server

```bash
uvicorn app.main:app --reload
```

- Interactive API docs (Swagger): http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## Run the tests

```bash
pytest --cov=app --cov-report=term-missing
```

## The two endpoints

Dev mode accepts the fake token `dev-supervisor` (and `dev-worker`) so you can
exercise the flow without a live Firebase project. The dev-supervisor token maps
to the **seeded** user `maria@flowforge.example`.

```bash
# READ — returns the seeded supervisor straight from the database
curl -s http://127.0.0.1:8000/auth/me -H "Authorization: Bearer dev-supervisor"

# WRITE — verifies the token, assigns the role, records a login event
curl -s -X POST http://127.0.0.1:8000/auth/login -H "Authorization: Bearer dev-supervisor"

# A worker gets role "worker"
curl -s -X POST http://127.0.0.1:8000/auth/login -H "Authorization: Bearer dev-worker"

# No token -> 401
curl -s -i http://127.0.0.1:8000/auth/me
```

## Inspect the database directly (handy for a demo)

```bash
python -c "import sqlite3; c=sqlite3.connect('flowforge.db'); \
[print(r) for r in c.execute('select uid,email,role from users')]"
```

## Production notes

- Set `DEV_MODE=false` and provide `FIREBASE_CREDENTIALS` + a Cloud SQL
  `DATABASE_URL` (MySQL, e.g. `mysql+pymysql://...`). All secrets come from
  environment variables.
- All DB access uses the SQLAlchemy ORM (parameterized) — no SQL injection.
- `.env` and any `*service-account*.json` are git-ignored.

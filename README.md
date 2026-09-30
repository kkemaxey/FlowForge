# FlowForge

A warehouse execution "control tower": a scaled-down take on a warehouse
execution system (WES) like Honeywell Intelligrated's, built for CSC 480.

**The core loop**

1. Orders come in and are turned into pick tasks.
2. A greedy assigner hands open tasks to idle workers and robots.
3. A simulator carries out the tasks and can raise exceptions (stockout, jam,
   worker down).
4. A supervisor watches throughput, work in progress and bottlenecks on a live
   console, and can reassign or expedite work.

## Status

**Sprint 0 (foundation).** The skeleton is in place, but no product features
exist yet:

- The backend has a `/health` endpoint and one empty router per module.
- The frontend has a Firebase login page and a sign-in-gated console with
  placeholder panels.
- Nothing is deployed yet.

Code freeze is **Dec 1, 2026**. See [`SPRINT_PLAN.md`](SPRINT_PLAN.md) for what
each sprint delivers and [`CHANGELOG.md`](CHANGELOG.md) for what has shipped.

## Scope

- **MVP (Sprint 2):** order intake, task generation, greedy assignment,
  simulated execution, workforce CRUD, an auth-gated console with reassign and
  expedite, and one exception flow with automatic reassignment.
- **Growth goals:** waves, a second exception type, SLA tracking, bottleneck
  highlighting.
- **Stretch goals:** real pathfinding, beating the greedy baseline, a separate
  picker app.

MVP work always comes before growth goals, and growth goals before stretch goals.

## Tech stack

| Part | Stack | Hosting |
|---|---|---|
| Frontend (`frontend/`) | Next.js (App Router), TypeScript, Tailwind | Vercel |
| Backend (`backend/`) | FastAPI, SQLAlchemy, Alembic | Google Cloud Run |
| Database | MySQL (SQLite by default for local development) | Google Cloud SQL |
| Auth | Firebase Authentication, single supervisor role | Firebase |
| Tests and CI | pytest, ESLint, GitHub Actions | GitHub |

## Team

| Person | Owns |
|---|---|
| Kanayo (team lead) | Orders, tasks, assignment; shared core |
| Kendyn | Simulation, exceptions, events and metrics |
| Brock | Auth (backend token check and login page) |
| Aalan | Console grid map and controls |
| Jayden | Console live board |
| Trent | Workforce, Docker and deploy, CI and test coverage |

[`ARCHITECTURE.md`](ARCHITECTURE.md) explains the folder layout, what each file
does and how the modules connect. Read it before your first PR.

## Repository layout

```
backend/
  app/
    main.py              app entry point; registers every module's router
    core/                config, database session, Firebase token check (shared)
    modules/<feature>/   router.py, models.py, schemas.py, service.py
  alembic/               database migrations
  tests/                 pytest tests
  Dockerfile
frontend/
  app/(auth)/login/      supervisor sign-in
  app/console/           console shell and panels: grid-map, controls, live-board, workforce
  components/ui/         shared UI components
  lib/                   API client and Firebase setup
  types/                 TypeScript types mirroring backend schemas
.github/
  CODEOWNERS             who reviews which folder
  workflows/ci.yml       tests, lint and build on every PR
```

## Running locally

### Backend

Requires Python 3.11 or newer.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # defaults use a local SQLite file
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

- Health check: http://127.0.0.1:8000/health
- Interactive API docs: http://127.0.0.1:8000/docs

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./flowforge.db` |
| `CORS_ORIGINS` | Comma-separated origins allowed to call the API | `http://localhost:3000` |
| `FIREBASE_CREDENTIALS` | Path to a Firebase service-account JSON | empty (uses Google default credentials) |

### Frontend

Requires Node 20 or newer.

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Open http://localhost:3000. The home page shows whether it can reach the
backend. Signing in and opening `/console` need the Firebase web config in
`.env.local`, from the Firebase console under **Project settings → Your apps**.

| Variable | Purpose |
|---|---|
| `NEXT_PUBLIC_API_URL` | Backend URL (default `http://localhost:8000`) |
| `NEXT_PUBLIC_FIREBASE_API_KEY`, `_AUTH_DOMAIN`, `_PROJECT_ID`, `_APP_ID` | Firebase web app config |

Never commit `.env`, `.env.local` or service-account JSON files.

## Tests

```bash
cd backend && pytest
cd frontend && npm run lint && npm run build
```

CI runs all of these on every pull request and on pushes to `main`.

## Contributing

1. Branch off `main` and stay inside the folders you own.
2. Open a pull request to `main`. It needs a review, and changes to another
   person's folder need that person's review (enforced by `CODEOWNERS`).
3. CI must pass before merging.
4. If you change a response shape in a `schemas.py`, update the matching type
   in `frontend/types/index.ts` in the same PR.
5. If you add or change a table, include an Alembic migration:
   `alembic revision --autogenerate -m "describe the change"`.

## Deployment

- **Backend:** built from `backend/Dockerfile` and run on Cloud Run, connected
  to Cloud SQL. Set `DATABASE_URL`
  (`mysql+pymysql://USER:PASS@/flowforge?unix_socket=/cloudsql/PROJECT:REGION:INSTANCE`),
  `CORS_ORIGINS` (the Vercel URL) and, if needed, `FIREBASE_CREDENTIALS`.
- **Frontend:** deployed on Vercel with root directory `frontend/`. Set
  `NEXT_PUBLIC_API_URL` to the Cloud Run URL, plus the Firebase variables, and
  add the Vercel domain to Firebase Auth's authorized domains.

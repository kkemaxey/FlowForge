# FlowForge Architecture

How the code is organized, who owns each part, and how the parts connect.
Read this before your first PR.

Each person owns one vertical slice of the app, and every slice plugs into a
small shared core that rarely changes. This lets six people work in parallel
without merge conflicts.

## The three layers

```
┌──────────────────────────── FRONTEND (browser, Vercel) ────────────────────────────┐
│  app/(auth)/login        app/console/…  (grid-map, controls, live-board, workforce)  │
│          │                          │                                               │
│          └──────── lib/firebase.ts  +  lib/api-client.ts  (shared) ─────────────────┤
└───────────────────────────────────┬─────────────────────────────────────────────────┘
                                    │  HTTP + Firebase token
┌───────────────────────────────────┴──────── BACKEND (FastAPI, Cloud Run) ───────────┐
│  main.py  ──includes──►  modules/<feature>/router.py                                │
│                               │ calls                                               │
│                          service.py  ──uses──►  models.py  (tables)                 │
│                                                 schemas.py (request/response shape) │
│  core/security.py (who's calling?)  core/database.py (DB session)  core/config.py   │
└───────────────────────────────────┬─────────────────────────────────────────────────┘
                                    │  SQLAlchemy / Alembic migrations
                            MySQL (Cloud SQL)
```

## Who owns what

Ownership is enforced by [`.github/CODEOWNERS`](.github/CODEOWNERS): a PR that
touches your folder needs your review.

| Person | Backend | Frontend | What they build |
|---|---|---|---|
| **Kanayo** | `modules/orders/`, `tasks/`, `assignment/` | none | Order intake, turning orders into tasks, the greedy assigner. Also reviews the shared core. |
| **Kendyn** | `modules/simulation/`, `events/` | none | Moving tasks through their states, exceptions (stockout or worker-down), the event log and metrics |
| **Brock** | `modules/auth/`, `core/security.py` | `app/(auth)/login/`, `lib/firebase.ts` | Sign-in and the token check that protects every route |
| **Trent** | `modules/workforce/`, `Dockerfile`, `tests/`, CI | `app/console/workforce/` | Worker/robot CRUD, deploy, CI and test coverage |
| **Aalan** | none | `app/console/grid-map/`, `controls/` | The warehouse map, and the reassign/expedite buttons |
| **Jayden** | none | `app/console/live-board/` | Order/task status board, throughput and WIP |
| **Shared** (Kanayo reviews) | `main.py`, `core/config.py`, `core/database.py`, `alembic/` | `lib/api-client.ts`, `types/`, `components/ui/` | Plumbing everyone uses. Changed rarely and carefully. |

## Inside one backend module

Every module in `backend/app/modules/` has the same four files:

| File | Job | Example (workforce) |
|---|---|---|
| `models.py` | Database table definitions | `Worker` table: name, type, speed, x/y, status |
| `schemas.py` | The shape of JSON going in and out | `WorkerCreate`, `WorkerOut` |
| `service.py` | The actual logic, with no HTTP details | `create_worker(db, data)`, `list_idle_workers(db)` |
| `router.py` | Endpoints that call the service | `POST /workforce`, `GET /workforce` |

The flow always goes **router → service → models**. Keep routers thin and put
logic in `service.py`, so it can be tested without running a server.

## How one request moves through the files

Example: the live board loads the task list.

1. `frontend/app/console/layout.tsx` checks that a supervisor is signed in,
   using `lib/firebase.ts`.
2. `console/live-board/LiveBoard.tsx` calls `apiFetch("/tasks")` in
   `lib/api-client.ts`, which attaches the Firebase token.
3. The request reaches the backend. `main.py` has already registered
   `modules/tasks/router.py`.
4. The endpoint depends on `core/security.get_current_user`, which verifies the
   token or returns 401, and on `core/database.get_db`, which opens a session.
5. The router calls `tasks/service.py`, which queries `tasks/models.py`.
6. The result is returned in the shape defined in `tasks/schemas.py`, which
   `frontend/types/index.ts` mirrors.

## How the modules talk to each other

```
orders ──creates──► tasks ◄──assigns── assignment ◄── idle workers ── workforce
                      ▲
                      └── advances state ── simulation ──logs──► events ──metrics──► live-board
```

- A module calls another module's `service.py` functions, never its routes or
  tables directly. For example, assignment calls `tasks.service` to get open
  tasks and `workforce.service` to get idle workers.
- If your change touches someone else's module, that person reviews the PR.

## Rules of thumb

- **Stay in your own folder.** A new endpoint goes in your `router.py`. A new
  table goes in your `models.py`, plus an Alembic migration
  (`alembic revision --autogenerate -m "..."` from `backend/`).
- **Don't edit `main.py`.** Your router is already included in it.
- **Keep types in sync.** When your `schemas.py` changes shape, update the
  matching type in `frontend/types/index.ts`.
- **Protect console endpoints.** Add `Depends(get_current_user)` from
  `app.core.security` to every route the console calls.
- **CI must pass.** Every PR runs backend tests and the frontend lint and build
  (`.github/workflows/ci.yml`). Add tests for your `service.py` in
  `backend/tests/`.

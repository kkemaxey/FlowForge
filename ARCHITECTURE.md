# FlowForge Architecture

How the code is organized and how the parts connect. To run it, see the
[README](README.md).

## The parts

```
┌────────────────────── FRONTEND (Next.js, browser) ──────────────────────┐
│  app/(portal)/console  ── grid map, controls, live board, workforce      │
│       │ poll every 2 s, or mock data if NEXT_PUBLIC_USE_MOCKS=true       │
│       └── lib/api-client.ts                                              │
└───────┬──────────────────────────────────────────────────────────────────┘
        │ HTTP, port 8080                 ┌───── SIMULATOR (separate process) ┐
        │ ◄───────────────────────────────┤ simulation/cli.py run             │
        ▼                                 │ acts as the workers, API only     │
┌──────────────── BACKEND (FastAPI, Docker) ────────────┐──────────────────┘
│  main.py ── includes ──► modules/<feature>/router.py   │
│                               │ calls                  │
│                          service.py ── models.py       │
│                                                        │
│  Background tasks in the same process:                 │
│    assigner loop (every 2 s), order generator          │
└───────┬────────────────────────────────────────────────┘
        │ SQLAlchemy, Alembic migrations
        ▼
     MySQL 8.0 (Docker)
```

The simulator only uses the HTTP API and has no database access, so it goes through the
same checks as any other client.

Auth is off for the MVP. `core/security.py` and `modules/auth/` exist, but no route
requires a login. There is one warehouse, so there is no `warehouses` table or
`warehouse_id`.

## Backend modules

| Module | Job | Tables |
|---|---|---|
| `orders` | Intake, stock allocation, order list, expedite | `orders`, `order_lines` |
| `tasks` | Task list and `transition()`, the task state machine | `tasks` |
| `assignment` | Greedy assigner, its 2-second loop, supervisor reassign | `assignments` |
| `simulation` | Picks, exceptions, rerouting, worker recovery, the simulator | `exceptions`, `sim_runs` |
| `events` | Metrics worked out from the event log | `events` |
| `workforce` | Worker create, edit and deactivate | `workers` |
| `warehouse` | Location list | `locations`, `skus`, `inventory` |
| `generator` | Streams random orders into intake, as a background task | none |
| `auth` | `POST /auth/session`, `GET /auth/me` (not yet applied to routes) | `users` |

`core/` holds what they share: config, the database session, the `{"detail", "code"}`
error format, request logging, and the UTC timestamp type.

Modules follow the same shape: `router.py` (endpoints), `service.py` (logic),
`models.py` (tables), `schemas.py` (JSON shapes). Requests go router → service → models,
so routers stay thin. Services import each other's models and functions where they need
to, because one action often spans several tables in one transaction.

## How an order moves through the system

```
POST /orders ─► orders.service   writes the order and lines, picks bins, reserves stock,
                                 creates tasks (open), all in one transaction
                    │
assigner loop ─► assignment      pairs idle workers with open tasks by Manhattan distance
                    │            task: open → assigned; worker: idle → busy
                    ▼
simulator ──polls── GET /simulation/assignments/active
    │               walks (distance ÷ speed), then picks (5 s), then one of:
    ├─ POST /tasks/{id}/pick        removes stock, closes the assignment, frees the
    │                               worker at the bin, completes the order on its last pick
    └─ POST /tasks/{id}/exceptions  stockout / jam: moves the task to the nearest bin that
                                    can cover it, or leaves it in exception for a supervisor
                                    worker_down: worker goes down, task reopens in place
```

Each step writes rows to `events`, which is what the metrics read.

## Task states

Every task status change goes through `transition()` in `tasks/service.py`.

```
open ──────► assigned ──────► picked (final)
 ▲  ◄──────── │  ▲ │
 │            │  └─┘ assigned → assigned: reassigned to another worker
 │            ▼
 └──────── exception ───► assigned (supervisor assigns it directly)
```

Orders are `open` or `complete`. A task never becomes `complete`: `picked` is final.
The live board labels picked tasks "Complete".

## Staying correct when things race

The assigner, simulator, generator and supervisor all write at once, so:

- **Tasks:** `transition()` is a compare-and-set on `status` and `version`. The loser gets
  a 409 instead of silently overwriting the winner.
- **One assignment at a time:** generated columns with unique keys allow at most one open
  assignment per task and per worker. MySQL has no partial unique indexes.
- **Stock:** intake and rerouting lock all of a SKU's inventory rows in `location_id` order,
  so they can't deadlock or over-reserve. The stock math is done in Python, because a
  stockout can leave more reserved than on hand, and MySQL errors when a subtraction of
  unsigned columns goes below zero.
- **Orders:** picks and exceptions lock the order first, so an order's work runs one at a
  time. This is what stops two simultaneous last picks from leaving an order open forever.
  Expedite takes its locks in the same order.
- **Workers:** routine status changes don't bump `workers.version`, which only guards
  supervisors' edits.
- **Events:** the table is append-only, enforced by database triggers.

## The frontend

Pages live in `app/(portal)/`, and the console's panels live in `app/console/`.

| Panel | Data |
|---|---|
| `grid-map/`, `controls/` | `ConsoleData.tsx`, one shared poll of workers and unfinished tasks |
| `live-board/` | `useLiveBoard.ts`, its own poll of orders, tasks and metrics |
| `workforce/` | Loads workers when it opens and after each edit |

Task lists are fetched one status at a time, because `GET /tasks` sorts oldest first and
finished tasks would otherwise push new ones off the list. `lib/api-client.ts` turns error
responses into `ApiRequestError`, with the backend's `code` and `detail`.

The Exceptions page, the console's exception feed and the admin pages are still wireframes.

## Rules of thumb

- **Schema changes need a new Alembic migration.** Never edit an existing one.
- **Change task status only through `transition()`**, and commit it together with the
  related writes.
- **Errors:** raise `ApiError(status_code, code, detail)`. A 409 always means a state conflict.
- **New routes go under `/api/v1`.** `/auth` is the current exception.
- **Keep types in sync** with the frontend when a `schemas.py` changes.
- **New modules:** add the router to `ROUTERS` in `main.py`.
- **Tests run on MySQL** with `docker compose exec backend pytest`, using the `floor`
  fixture in `tests/conftest.py`.

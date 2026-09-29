# FlowForge — Design Doc (initial draft)

**Author:** Jayden Keaton (Frontend / Console Support: live board, throughput/WIP views)
**Course:** CSC 480, Fall 2026 · **Version:** 0.3.0 · **Code freeze:** Dec 1, 2026

## Problem

Maria is a shift supervisor at a regional third-party-logistics distribution center. She finds
late orders and idle workers by walking the floor and radioing pickers, then updates a shared
spreadsheet by hand. When a bin runs out mid-shift she only hears about it once a picker radios
in, and by then the order is already behind. FlowForge replaces that loop with a control tower:
orders become pick tasks, tasks are assigned to workers, and a live board shows what is late,
stuck or blocked so Maria can reassign or expedite before an order misses its window.

## Minimal Viable Product

1. **Order intake → pick tasks.** Each order line becomes a pick task for a SKU, storage location
   and quantity; the order carries the due time.
2. **Task lifecycle.** Tasks move `open → assigned → picked`; an assigned task can hit an
   `exception` (stockout, jam) and goes back to `open` to be reassigned.
3. **Assignment.** Tasks are assigned to workers (greedy scheduler in the team build; manual
   assignment through the API in this slice).
4. **Live supervisor board.** One screen with orders by status, tasks in status columns (expedited
   orders on top, late ones flagged), and WIP / exception / last-hour throughput counts.
5. **Reassign and expedite** controls on the board.
6. **Workforce CRUD** and **minimal auth** with a single supervisor role.

This branch delivers item 1 (intake and task generation), item 2, item 4 and expedite from item 5
as a working backend slice.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js + TypeScript (hosted on Vercel) |
| Backend | FastAPI on Python 3.11+ (developed on 3.14), hosted on Google Cloud Run |
| Database | MySQL 8.4 via SQLAlchemy 2.1 + PyMySQL; Google Cloud SQL in production, Docker locally |
| Auth | Firebase Authentication (supervisor role modeled in app code) |
| Testing | pytest, pytest-cov, FastAPI TestClient |
| Versioning | SemVer, `GitVersion.yaml` + `CHANGELOG.md` |

Rationale for each choice is in the team Architecture Decision Record.

## Data model

Table and column names follow the course spec, so this branch merges cleanly with teammates' work.

```
orders(id, created_at, due_at, status, priority)   status: new | in_progress | complete | late
order_lines(id, order_id, sku_id, qty)
tasks(id, order_line_id, sku_id, location_id, qty, status)   status: open | assigned | picked | exception
assignments(id, task_id, worker_id, assigned_at, completed_at)
```

`priority` (`normal` | `expedite`) is the one addition, so a supervisor can expedite an order.
`late` is worked out when the order is read: any unfinished order past `due_at`. The `locations`,
`skus` and `inventory` tables arrive with the instructor's seed; until then an order line carries
its `location_id` (for example `A1-01`).

## Backend structure

```
backend/app/
  core/            config (env vars), database, logging, errors, version, clock
  modules/orders/
    task_states.py   task lifecycle rules     ─┐
    order_status.py  order status rules        │
    service.py       intake + business rules   ├─ business layer (unit tested)
    board.py         live-board builder       ─┘
    repository.py    SQLAlchemy queries (ORM only, bound parameters)
    router.py        HTTP endpoints
```

The router only translates HTTP to service calls. The service never touches SQL; it talks to a
repository, which unit tests replace with an in-memory fake.

## API contract examples

All errors share one shape: `{"error": {"code": "...", "message": "...", "details": [...]}}`.
Times are ISO 8601 UTC with a trailing `Z`.

### `POST /api/orders` — take in an order → `201 Created`

```json
// request
{ "due_at": "2026-10-01T15:30:00Z", "priority": "normal",
  "lines": [ { "sku_id": "SKU-88213", "qty": 4, "location_id": "A1-01" },
             { "sku_id": "SKU-10007", "qty": 1, "location_id": "C4-11" } ] }

// response: the order plus one generated task per line
{ "id": 1, "status": "new", "priority": "normal",
  "created_at": "2026-10-01T14:50:12Z", "due_at": "2026-10-01T15:30:00Z",
  "tasks": [ { "id": 1, "order_id": 1, "order_line_id": 1, "sku_id": "SKU-88213",
               "location_id": "A1-01", "qty": 4, "status": "open",
               "worker_id": null, "assigned_at": null, "completed_at": null },
             { "id": 2, "...": "..." } ] }
```

`422` if a field is invalid (e.g. `location_id` not like `A1-01`, `qty` ≤ 0, no lines, `due_at` in the past).

### `PATCH /api/tasks/{id}/status` — move through the lifecycle → `200 OK`

```json
{ "status": "assigned", "worker_id": 2 }   // records an assignment
{ "status": "picked" }                     // completes it; order becomes complete when all tasks are
{ "status": "exception" }                  // stockout or jam
{ "status": "open" }                       // back to the pool for reassignment
```

`404` unknown task · `409` transition not allowed:

```json
{ "error": { "code": "invalid_transition",
             "message": "Cannot move a task from 'open' to 'picked'." } }
```

### `GET /api/board` — live supervisor board → `200 OK`

```json
{ "generated_at": "2026-10-01T14:55:00Z",
  "summary": { "total_tasks": 3, "work_in_progress": 1, "exceptions": 0,
               "late_orders": 1, "picked_last_hour": 0 },
  "orders_by_status": { "new": 1, "in_progress": 1, "complete": 0, "late": 1 },
  "columns": {
    "open": [ { "task_id": 2, "order_id": 2, "priority": "expedite", "is_late": false,
                "minutes_until_due": 85, "location_id": "C4-11", "...": "..." },
              { "task_id": 1, "order_id": 1, "priority": "normal", "is_late": true,
                "minutes_until_due": -4, "...": "..." } ],
    "assigned": [ { "task_id": 3, "worker_id": 5, "...": "..." } ],
    "picked": [], "exception": [] } }
```

### Other endpoints

| Method | Path | Purpose | Codes |
|---|---|---|---|
| GET | `/api/orders/{id}` | An order and its tasks | 200, 404 |
| POST | `/api/orders/{id}/expedite` | Raise an order to expedite priority | 200, 404, 422 |
| GET | `/api/tasks?status=open` | List tasks, optional status filter | 200, 422 |
| GET | `/api/tasks/{id}` | One task | 200, 404 |
| GET | `/health` | Version and database connectivity | 200, 503 |

Interactive docs: `http://127.0.0.1:8000/docs` while the server runs.

## Features under consideration

- Live board that refreshes on its own (polling first, WebSocket/SSE later)
- Throughput and WIP charts over the shift
- Late-order and stockout alerts
- Drag-and-drop reassignment on the board
- Expedite / de-expedite controls
- Grid map of worker and robot positions
- Greedy task assignment, then smarter pathfinding ("beat the greedy")
- Wave / batch planning
- Exception handling flow (bin empty, damaged item, can't find SKU)
- Worker simulator for demos
- Workforce management (add, edit, disable workers and robots)
- Firebase login with a supervisor role
- Shift summary report / CSV export

## Security, logging, configuration

- Credentials come only from environment variables (`DATABASE_URL`); `.env` is git-ignored and
  `.env.example` holds placeholders.
- Every query goes through the SQLAlchemy ORM with bound parameters; input is validated by
  Pydantic before it reaches the service. An integration test stores a SQL-injection string and
  confirms it is saved as plain text.
- Every request is logged when it arrives and when it completes, with method, path, status,
  duration and an `X-Request-ID` echoed back to the client.

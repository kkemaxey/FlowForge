# FlowForge — Design Doc (initial draft)

**Author:** Jayden Keaton (Frontend / Console Support: live board, throughput/WIP views)
**Course:** CSC 480, Fall 2026 · **Version:** 0.2.0 · **Code freeze:** Dec 1, 2026

## Problem

Maria is a shift supervisor at a regional third-party-logistics distribution center. She finds
late orders and idle workers by walking the floor and radioing pickers, then updates a shared
spreadsheet by hand. When a bin runs out mid-shift she only hears about it once a picker radios
in, and by then the order is already behind. FlowForge replaces that loop with a control tower:
orders become pick tasks, tasks are assigned to workers, and a live board shows what is late,
stuck or blocked so Maria can reassign or expedite before an order misses its window.

## Minimal Viable Product

1. **Order intake → pick tasks.** Each order line becomes a pick task with a SKU, bin location,
   quantity and due time.
2. **Task lifecycle.** Tasks move `open → assigned → in_progress → picked`, and any active task
   can go to `exception` (e.g. bin empty) and back to `open` once resolved.
3. **Assignment.** Tasks are assigned to workers (greedy scheduler in the team build; manual
   assignment through the API in this slice).
4. **Live supervisor board.** One screen with tasks in status columns, expedited work on top,
   late tasks flagged, and WIP / exception / last-hour throughput counts.
5. **Reassign and expedite** controls on the board.
6. **Workforce CRUD** and **minimal auth** with a single supervisor role.

This branch delivers items 2, 4 and the expedite half of 5 as a working backend slice.

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

## Backend structure

```
backend/app/
  core/            config (env vars), database, logging, errors, version, clock
  modules/tasks/
    task_states.py   lifecycle rules          ─┐
    service.py       business rules            ├─ business layer (unit tested)
    board.py         live-board builder       ─┘
    repository.py    SQLAlchemy queries (ORM only, bound parameters)
    router.py        HTTP endpoints
```

The router only translates HTTP to service calls. The service never touches SQL; it talks to a
repository, which unit tests replace with an in-memory fake.

## API contract examples

All errors share one shape: `{"error": {"code": "...", "message": "...", "details": [...]}}`.
Times are ISO 8601 UTC with a trailing `Z`.

### `POST /api/tasks` — create a pick task → `201 Created`

```json
// request
{ "order_ref": "ORD-10442", "sku": "SKU-88213", "bin_location": "B-07-3",
  "quantity": 4, "priority": "normal", "due_at": "2026-10-01T15:30:00Z" }

// response
{ "id": 1, "order_ref": "ORD-10442", "sku": "SKU-88213", "bin_location": "B-07-3",
  "quantity": 4, "priority": "normal", "status": "open", "assigned_worker_id": null,
  "due_at": "2026-10-01T15:30:00Z", "created_at": "2026-10-01T14:50:12Z",
  "updated_at": "2026-10-01T14:50:12Z", "completed_at": null, "exception_reason": null }
```

`422` if a field is invalid (e.g. `bin_location` not like `B-07-3`, `quantity` ≤ 0, `due_at` in the past).

### `PATCH /api/tasks/{id}/status` — move through the lifecycle → `200 OK`

```json
{ "status": "assigned", "worker_id": 2 }
{ "status": "in_progress" }
{ "status": "exception", "reason": "Bin B-07-3 empty" }
{ "status": "picked" }
```

`404` unknown task · `409` transition not allowed:

```json
{ "error": { "code": "invalid_transition",
             "message": "Cannot move a task from 'open' to 'picked'." } }
```

### `GET /api/board` — live supervisor board → `200 OK`

```json
{ "generated_at": "2026-10-01T14:55:00Z",
  "summary": { "total_tasks": 3, "work_in_progress": 1, "late_tasks": 1,
               "exceptions": 0, "picked_last_hour": 0 },
  "columns": {
    "open": [ { "id": 2, "order_ref": "RUSH-7", "priority": "expedite", "is_late": false,
                "minutes_until_due": 85, "bin_location": "A-02-1", "...": "..." },
              { "id": 1, "order_ref": "ORD-10442", "priority": "normal", "is_late": true,
                "minutes_until_due": -4, "...": "..." } ],
    "assigned": [ { "id": 3, "assigned_worker_id": 5, "...": "..." } ],
    "in_progress": [], "picked": [], "exception": [] } }
```

### Other endpoints

| Method | Path | Purpose | Codes |
|---|---|---|---|
| GET | `/api/tasks?status=open` | List tasks by due time, optional status filter | 200, 422 |
| GET | `/api/tasks/{id}` | One task | 200, 404 |
| POST | `/api/tasks/{id}/expedite` | Raise to expedite priority | 200, 404, 422 |
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

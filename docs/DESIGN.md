# FlowForge — Design Doc (initial draft)

**Author:** Jayden Keaton (Frontend / Console Support: live board, throughput/WIP views)
**Course:** CSC 480, Fall 2026 · **Version:** 0.4.0 · **Code freeze:** Dec 1, 2026

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

This branch delivers the create and list half of item 6 (workforce management) as a working
backend slice: a supervisor can add a human or robot worker and see everyone on the floor.

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

The `workers` table follows the course spec, so this branch merges cleanly with teammates' work.

```
workers(id, name, type, speed, cur_x, cur_y, status, enabled)
  type:   human | robot
  status: idle | busy
```

`name` is unique (ignoring case). `cur_x` and `cur_y` are a cell on the 20 × 12 floor grid from
the course map seed; new workers start at the dock, (0, 0), unless a position is given.

## Backend structure

```
backend/app/
  core/               config (env vars), database, logging, errors, version
  modules/workforce/
    schema.py         request/response shapes, field rules (grid bounds, allowed values)  ─┐ business layer
    service.py        business rules: speed limits, no duplicate names, busy needs enabled ─┘ (unit tested)
    repository.py     SQLAlchemy queries (ORM only, bound parameters)
    router.py         HTTP endpoints
```

The router only translates HTTP to service calls. The service never touches SQL; it talks to a
repository, which unit tests replace with an in-memory fake.

## Business rules

| Rule | Error |
|---|---|
| `name` required, whitespace tidied, max 60 characters | 422 |
| `type` is `human` or `robot`; `status` is `idle` or `busy` | 422 |
| `speed` > 0, at most **2.0** for a human and **4.0** for a robot (grid cells per second) | 422 |
| `cur_x` in 0–19, `cur_y` in 0–11 | 422 |
| A disabled worker cannot be `busy` | 422 |
| No two workers share a name (case-insensitive) | 409 |

## API contract examples

All errors share one shape: `{"error": {"code": "...", "message": "...", "details": [...]}}`.

### `POST /api/workers` — add a worker → `201 Created`

```json
// request (cur_x, cur_y, status and enabled are optional)
{ "name": "Maria Lopez", "type": "human", "speed": 1.2, "cur_x": 3, "cur_y": 5 }

// response
{ "id": 1, "name": "Maria Lopez", "type": "human", "speed": 1.2,
  "cur_x": 3, "cur_y": 5, "status": "idle", "enabled": true }
```

`409` if the name is taken:

```json
{ "error": { "code": "conflict", "message": "A worker named 'maria lopez' already exists." } }
```

`422` for invalid input, naming each bad field:

```json
{ "error": { "code": "validation_failed", "message": "Request body or parameters are invalid.",
             "details": [ { "field": "body.type", "message": "Input should be 'human' or 'robot'" },
                          { "field": "body.cur_x", "message": "Input should be less than 20" } ] } }
```

### `GET /api/workers` — list workers → `200 OK`

Optional filters: `?type=human|robot` and `?status=idle|busy`. Workers come back in the order
they were added.

```json
[ { "id": 1, "name": "Maria Lopez", "type": "human", "speed": 1.2,
    "cur_x": 3, "cur_y": 5, "status": "idle", "enabled": true },
  { "id": 2, "name": "PickBot-7", "type": "robot", "speed": 3.5,
    "cur_x": 0, "cur_y": 0, "status": "idle", "enabled": true } ]
```

### Other endpoints

| Method | Path | Purpose | Codes |
|---|---|---|---|
| GET | `/health` | Version and database connectivity | 200, 503 |

Interactive docs: `http://127.0.0.1:8000/docs` while the server runs.

## Features under consideration

- Edit, disable and remove workers (the rest of workforce CRUD)
- Live board that refreshes on its own (polling first, WebSocket/SSE later)
- Throughput and WIP charts over the shift
- Late-order and stockout alerts
- Order intake that generates pick tasks
- Drag-and-drop reassignment on the board
- Grid map of worker and robot positions
- Greedy task assignment, then smarter pathfinding ("beat the greedy")
- Worker simulator for demos
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

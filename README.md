# FlowForge

A warehouse execution "control tower": a scaled-down take on a warehouse
execution system (WES), built for CSC 480.

**The core loop**

1. Orders come in and are turned into pick tasks, reserving stock in specific bins.
2. A greedy assigner hands open tasks to idle workers and robots every 2 seconds.
3. A simulator carries out the tasks and can raise exceptions (stockout, jam,
   worker down).
4. A supervisor watches throughput, work in progress and exceptions on a live
   console, and can reassign or expedite work.

## Status

**The MVP loop works end to end.** Orders flow from intake through assignment and
picking to completion, with exceptions, rerouting and a live console. See
[Known limitations](#known-limitations) for what's left out, and
[`CHANGELOG.md`](CHANGELOG.md) for what has shipped.

Authentication is **off** for the MVP: every endpoint is open, so don't expose
this to the internet as is.

## Tech stack

| Part | Stack |
|---|---|
| Frontend (`frontend/`) | Next.js (App Router), React, TypeScript, Tailwind |
| Backend (`backend/`) | FastAPI, SQLAlchemy, Alembic, Python 3.12 |
| Database | MySQL 8.0 |
| Running it | Docker Compose for MySQL and the backend; Node for the frontend |
| Tests and CI | pytest on MySQL, ESLint, GitHub Actions |

## Running locally

You need Docker Desktop, Node 20 or newer, and git, with 5–10 GB of free disk.

**1. Start the backend and database**

```bash
cp backend/.env.example backend/.env                # then replace the change-me passwords
docker compose up -d --build                        # MySQL and the backend on port 8080
docker compose exec backend alembic upgrade head    # create the tables
docker compose exec backend python -m app.seed      # load the demo warehouse
```

- API docs: http://localhost:8080/docs
- Health check: http://localhost:8080/health

**2. Start the frontend**

```bash
cd frontend
npm ci
cp .env.example .env.local      # set NEXT_PUBLIC_USE_MOCKS=false to use the real backend
npm run dev
```

Open http://localhost:3000/console. With `NEXT_PUBLIC_USE_MOCKS=true`, the default,
the console runs on in-browser mock data and needs no backend. Restart `npm run dev`
after changing this setting.

## Running the demo

1. Start the simulator in its own terminal. It keeps running until you press Ctrl+C.

   ```bash
   docker compose exec backend python -m app.modules.simulation.cli run
   ```

2. On the console, under **Order generator**, click **Start**. You can also call
   `POST /api/v1/generator/start` with `{"order_rate": 6, "seed": 480}` to set the rate.
3. Watch workers pick up tasks on the grid and orders complete on the live board.
4. Reassign a stuck task or expedite an order from the controls.

To force a failure on a task that's currently assigned:

```bash
docker compose exec backend python -m app.modules.simulation.cli trigger --task-id 42 --type stockout
```

The types are `stockout`, `jam` and `worker_down`. To raise the random rates, pass
flags such as `--p-jam 0.15` to `run`. The defaults are in
[`backend/.env.example`](backend/.env.example).

**What to expect**

- **Stock runs out.** The seed holds 624 pairs and picks only remove stock. Orders
  average about 4 pairs, so that's about 5 minutes at 30 orders/min or 26 at 6/min.
  Low-stock shoes run out much sooner.
- **Rejected orders are intended.** An order that stock can't cover gets a 409
  `insufficient_stock` and writes nothing. The generator counts these.
- **Some exceptions wait for a supervisor.** A jam or stockout with no other bin to
  move to leaves the task in `exception` until someone reassigns it.

**Reset between runs.** This gives you full stock again:

```bash
docker compose exec backend alembic downgrade base
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seed
```

## API

All routes are under `/api/v1`, except `/health` and `/auth`. The full reference is at
http://localhost:8080/docs.

| Area | Endpoints |
|---|---|
| Orders | `GET`, `POST /orders`; `GET /orders/{id}`; `POST /orders/{id}/expedite` |
| Tasks | `GET /tasks`; `POST /tasks/{id}/reassign`, `/pick`, `/exceptions` |
| Exceptions | `GET /exceptions` |
| Workers | `GET`, `POST /workers`; `GET`, `PATCH`, `DELETE /workers/{id}` |
| Warehouse | `GET /locations` |
| Metrics | `GET /events/metrics`; `GET /events/metrics/throughput` |
| Generator | `GET /generator`; `POST /generator/start`, `/stop` |
| Assigner | `POST /assignments/run` runs one pass by hand |
| Simulator | `GET /simulation/assignments/active`; `POST /simulation/workers/{id}/recover` |

Errors are always `{"detail", "code"}`. A 409 always means a state conflict, such as
`version_conflict` or `invalid_transition`.

## Known limitations

- **The assigner only looks at distance.** `greedy_v1` pairs by Manhattan distance.
  Expedite moves an order to the front of the queue but doesn't change who gets assigned.
- **Auth is off.** The login page and `/auth` endpoints exist, but no route requires
  a login.
- **Some pages are wireframes.** The Exceptions page, the console's exception feed and
  the admin pages are placeholders. The exception data is available from `GET /exceptions`.
- **One backend instance.** The assigner loop assumes a single instance.
- **Stuck tasks hold no stock.** Other orders can take that stock in the meantime, so a
  reassigned task can hit another stockout.
- **The simulator keeps its recovery list in memory.** Restart it during an outage and
  that worker stays down until `POST /simulation/workers/{id}/recover`.

## Scope

- **MVP:** order intake, task generation, greedy assignment, simulated execution,
  workforce management, a console with reassign and expedite, and exception handling
  with automatic rerouting.
- **Growth goals:** waves, SLA tracking, bottleneck highlighting.
- **Stretch goals:** real pathfinding, beating the greedy baseline, a separate
  picker app.

## Tests

```bash
docker compose exec backend pytest -q
cd frontend && npm run lint && npm run build
```

Backend tests run against a separate MySQL test database, never the dev one. CI runs
the tests, the frontend lint and build, and a Docker build on every pull request and
on pushes to `main`.

## Repository layout

```
backend/
  app/
    main.py              app entry point; registers every module's router
    seed.py              the demo warehouse
    core/                config, database, errors, request logging, Firebase token check
    modules/<feature>/   router.py, models.py, schemas.py, service.py
  alembic/versions/      database migrations (latest: 0004)
  tests/
frontend/
  app/(portal)/          pages: console, metrics, exceptions, orders, admin
  app/console/           console panels: grid-map, controls, live-board, workforce
  components/, lib/, types/, mocks/
docker-compose.yml       MySQL and the backend for local development
```

[`ARCHITECTURE.md`](ARCHITECTURE.md) explains how the parts connect.

## Team

| Person | Worked on |
|---|---|
| Kanayo (team lead) | Schema, orders, tasks, assignment, generator; integration |
| Kendyn | Simulator, exceptions, picking, metrics |
| Brock | Auth |
| Aalan | Grid map and controls |
| Jayden | Live board and portal pages |
| Trent | Workforce, request logging, CI |

## Contributing

1. Branch off `main` and open a pull request. It needs one approval, with all review
   conversations resolved and CI passing.
2. Change a table only through a new Alembic migration. Never edit an existing one.
3. If you change a response in a `schemas.py`, update the matching frontend type in
   the same PR.
4. Never commit `.env`, `.env.local` or service-account files.

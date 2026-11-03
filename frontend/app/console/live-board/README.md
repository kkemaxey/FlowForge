# Live board

Shows order and task status, throughput, WIP, on-time % and active exceptions on `/console`, polling every
2 seconds. Also renders the throughput chart on `/metrics`.

| File | Job |
|---|---|
| `LiveBoard.tsx` | The board UI |
| `KpiStrip.tsx` | Throughput, WIP and on-time % tiles |
| `ThroughputChart.tsx` | Units per minute over the last 30 minutes (metrics page) |
| `useLiveBoard.ts` | Polls orders, tasks and metrics; metrics are optional |
| `boardLogic.ts` | Calculations behind the UI: task counts, WIP, exceptions, on-time %, sorting, throughput summary |
| `data.ts` | The board's types, the getters, and the mapping from the backend's shapes onto those types |
| `mockData.ts` | In-browser simulator used while `NEXT_PUBLIC_USE_MOCKS=true` |

## Mock vs. real API

`NEXT_PUBLIC_USE_MOCKS` in `frontend/.env.local` picks the data source. It defaults to `"true"`. Set it to
`"false"` (and `NEXT_PUBLIC_API_URL=http://localhost:8080`) to call the backend. Next.js inlines these at build
time, so restart `npm run dev` after changing them. A Firebase token is attached only when the
`NEXT_PUBLIC_FIREBASE_*` values are set.

## What the board calls

| Request | Used for | Status |
|---|---|---|
| `GET /api/v1/tasks?limit=500` | Tasks, task counts, WIP, exceptions, and which orders to show | Exists |
| `GET /api/v1/orders/{id}` | One request per order, for the 14 newest order ids found in the tasks | Exists |
| `GET /api/v1/events/metrics` | Throughput tile and the active exception | Not in the backend yet; the tile shows a dash |
| `GET /api/v1/events/metrics/throughput?minutes=30` | Metrics page chart | Not in the backend yet; the chart says so |

Orders and tasks are required: if either fails, the last good data stays on screen with an error. Metrics are
optional: if they fail, everything else still updates.

## How `data.ts` maps the backend

| Backend | Board |
|---|---|
| `task_id`, `sku_code`, `qty` | `id`, `sku`, `quantity` |
| `location` `{location_id, x, y, zone, aisle}` | `location` label like `"A3 (7,3)"` (the backend has no bin code) |
| `current_assignment.worker_id` | `worker_id` (`null` when unassigned) |
| task `picked` (final state) | `complete` |
| order `complete` | `complete` |
| order `open` past `due_at` | `late` |
| order `open` with any task past `open` | `in_progress` |
| order `open`, all tasks `open` | `new` |

## Gaps for the backend

- **No order list.** A `GET /api/v1/orders?limit=14` (newest first) would replace the per-order requests.
- **No metrics.** Throughput needs completions over time, e.g. `GET /api/v1/events/metrics` returning
  `{units_per_hour, tasks_per_hour, active_exception, as_of}` and `/throughput` returning
  `[{bucket_start, units, tasks}]` per minute, oldest first.
- **No `completed_at` on orders**, so on-time % shows a dash with real data.
- **No exception type on tasks**, so the banner labels every exception a stockout.

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

| Request | Used for |
|---|---|
| `GET /api/v1/tasks?status=…&limit=500` | Task counts, WIP and exceptions. One request each for `open`, `assigned`, `picked` and `exception` |
| `GET /api/v1/orders?limit=200` | The orders table, WIP and on-time % |
| `GET /api/v1/events/metrics` | Throughput tile and the active exception |
| `GET /api/v1/events/metrics/throughput?minutes=30` | Metrics page chart |

Orders and tasks are required: if either fails, the last good data stays on screen with an error. Metrics are
optional: if they fail, everything else still updates. Every request times out after 8 seconds
(`lib/api-client.ts`), so a hung call can't stop the polling.

## How `data.ts` maps the backend

| Backend | Board |
|---|---|
| `task_id`, `sku_code`, `qty` | `id`, `sku`, `quantity` |
| `location` `{location_id, x, y, zone, aisle}` | `location` label like `"A3 (7,3)"` (the backend has no bin code); an order line split across bins lists each one |
| `current_assignment.worker_id` | `worker_id` (`null` when unassigned) |
| task `picked` (final state) | `complete` |
| order `complete` | `complete` |
| order `open` past `due_at` | `late` |
| order `open` with any task past `open` | `in_progress` |
| order `open`, all tasks `open` | `new` |

## Known limits

- **Exception type.** `GET /tasks` doesn't return it, so the banner shows a plain "Exception" for most tasks.
  `GET /api/v1/exceptions` has the type if the banner needs it later.
- **`updated_at`.** `TaskOut` doesn't return it, so the field is `null` with real data.
- **Counts are capped.** The Complete count stops at 500 and the orders list at the newest 200, which the seeded
  stock doesn't reach. A counts endpoint would remove both caps.

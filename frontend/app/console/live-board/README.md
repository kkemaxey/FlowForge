# Live board

Owner: Jayden. Shows order and task status, throughput, WIP and active exceptions. Polls every 2 seconds.

| File | Job |
|---|---|
| `LiveBoard.tsx` | The board UI |
| `useLiveBoard.ts` | Polls all three endpoints, tracks loading/error |
| `boardLogic.ts` | Calculations behind the UI: exception list, WIP total, order sorting |
| `data.ts` | Types and `getOrders()` / `getTasks()` / `getMetrics()` |
| `mockData.ts` | In-browser simulator used until the backend endpoints exist |

## Mock vs. real API

`NEXT_PUBLIC_USE_MOCKS` in `frontend/.env.local` picks the data source. It defaults to `"true"`. Set it to
`"false"` to call the backend through `apiFetch` (Firebase token attached). Next.js inlines the value at build
time, so restart `npm run dev` after changing it.

## Endpoints the board needs

All three are `GET`, need the Firebase token, and return JSON. Timestamps are ISO 8601 strings in UTC
(`"2026-10-17T18:04:12Z"`). IDs are integers. Field names are snake_case, matching the Pydantic schemas.

### `GET /orders` (Kanayo)

Returns an array of orders, each with its lines.

```json
[
  {
    "id": 1001,
    "status": "in_progress",
    "created_at": "2026-10-17T18:00:00Z",
    "due_at": "2026-10-17T18:30:00Z",
    "completed_at": null,
    "lines": [
      { "id": 1, "order_id": 1001, "sku": "SKU-1042", "quantity": 3, "location": "A-03-2" }
    ]
  }
]
```

- `status`: `"new" | "in_progress" | "complete" | "late"`
  - `new`: no task has started
  - `in_progress`: at least one task is past `open`
  - `complete`: every task is `complete`
  - `late`: past `due_at` and not complete
- `completed_at`: set when the order becomes `complete`, otherwise `null`

### `GET /tasks` (Kanayo)

Returns an array of pick tasks, one per order line.

```json
[
  {
    "id": 7,
    "order_id": 1001,
    "order_line_id": 1,
    "sku": "SKU-1042",
    "quantity": 3,
    "location": "A-03-2",
    "status": "assigned",
    "worker_id": 4,
    "exception_type": null,
    "updated_at": "2026-10-17T18:04:12Z"
  }
]
```

- `status`: `"open" | "assigned" | "picked" | "complete" | "exception"`. `exception` is new; the shared
  `TaskStatus` in `types/index.ts` needs it added.
- `worker_id`: `null` while `open`
- `exception_type`: `"stockout" | "worker_down"` when `status` is `"exception"`, otherwise `null`

### `GET /events/metrics` (Kendyn)

```json
{
  "units_per_hour": 312,
  "tasks_per_hour": 104,
  "orders_in_progress": 5,
  "tasks_assigned": 4,
  "task_counts": { "open": 6, "assigned": 4, "picked": 2, "complete": 18, "exception": 1 },
  "active_exception": {
    "task_id": 12,
    "order_id": 1004,
    "location": "C-07-1",
    "type": "stockout",
    "raised_at": "2026-10-17T18:05:40Z"
  },
  "as_of": "2026-10-17T18:06:00Z"
}
```

- `units_per_hour` / `tasks_per_hour`: units and tasks completed over a recent window (the mock uses the last
  5 minutes), scaled to an hourly rate
- `orders_in_progress`: orders with status `in_progress` or `late`
- `tasks_assigned`: tasks with status `assigned`. The board shows WIP as `orders_in_progress + tasks_assigned`
- `task_counts`: include every status key, even when the count is 0
- `active_exception`: the current unresolved exception, or `null`. `type` is `"stockout" | "worker_down"`.
  The board also flags any task in `GET /tasks` with status `exception`, so either source works.

## TODO

- Move `Order`, `OrderLine`, `Task`, `LiveMetrics` and `LiveTaskStatus` from `data.ts` into `types/index.ts`
  after Kanayo reviews them.

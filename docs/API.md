# FlowForge API

Base URL (local): `http://127.0.0.1:8000` · Interactive docs: `/docs` · OpenAPI JSON: `/openapi.json`

## Error format

Every error response has the same body (the one exception is the `/health` 503, shown under
[Health](#health)):

```json
{"error": {"code": "worker_not_found", "message": "Worker 7 does not exist"}}
```

| Status | When | Codes |
|---|---|---|
| 404 | Resource or route does not exist | `worker_not_found`, `not_found` |
| 405 | Wrong HTTP method for a path | `method_not_allowed` |
| 409 | Request conflicts with current state | `worker_busy` |
| 422 | Malformed input or a broken business rule | `validation_error`, `position_off_grid`, `task_id_required`, `qty_required`, `invalid_window` |
| 500 | Unexpected server error (details are logged, not returned) | `internal_error` |
| 503 | Database unreachable (health check only) | — |

`validation_error` covers anything Pydantic rejects: a missing or wrongly typed field, a value out of
range, an unknown field (including `status`, which clients may never set), an explicit `null` in a
PATCH, or a non-integer path/query parameter such as `/api/workers/abc`.

Responses include an `X-Request-ID` header. Send your own to correlate with server logs; otherwise the
server generates one. The header is **not** set on unexpected `500` responses, but the id still
appears in the server's `request failed` log line.

## Health

### `GET /health`
Service version and database connectivity.
- `200` `{"status": "ok", "version": "0.1.0", "db": "ok"}`
- `503` `{"status": "degraded", "version": "0.1.0", "db": "unreachable"}`

## Workers

Worker fields: `id` (int), `name` (1–64 chars), `type` (`human` | `robot`), `speed` (0.1–10.0),
`cur_x` (0 ≤ x < 20), `cur_y` (0 ≤ y < 12), `status` (`idle` | `busy`, read-only), `enabled` (bool).

### `GET /api/workers?status=&type=`
List workers, optionally filtered. `200` array of workers · `422 validation_error` invalid filter value.

### `GET /api/workers/{id}`
`200` worker · `404 worker_not_found` · `422 validation_error` (non-integer id).

### `POST /api/workers`
Create a worker; it starts `idle`. `enabled` is optional and defaults to `true`.

```json
{"name": "Picker Ana", "type": "human", "speed": 1.5, "cur_x": 3, "cur_y": 4}
```

`201` worker plus `Location: /api/workers/{id}` · `422 validation_error` (bad field, or `status` sent) ·
`422 position_off_grid`.

### `PATCH /api/workers/{id}`
Change any of `name`, `type`, `speed`, `cur_x`, `cur_y`, `enabled`. Omitted fields are unchanged; `null` is rejected.
Sending `status` is rejected with `422 validation_error`.

```json
{"enabled": false}
```

`200` updated worker · `404 worker_not_found` · `422 validation_error` / `position_off_grid`.

### `DELETE /api/workers/{id}`
`204` no body · `404 worker_not_found` · `409 worker_busy`.

## Events and metrics

### `POST /api/events`
Record a warehouse event. The server sets `ts`.

| `type` | Required fields |
|---|---|
| `task_assigned` | `task_id` |
| `task_picked` | `task_id`, `qty` ≥ 1 |
| `task_exception` | `task_id` (put the reason in `payload`) |
| `order_completed` | none |

```json
{"type": "task_picked", "task_id": 42, "worker_id": 3, "qty": 2}
```

`201` stored event with `id` and `ts` · `422 validation_error` / `task_id_required` / `qty_required`.

`ts` is returned as an ISO-8601 UTC timestamp without a timezone suffix, e.g.
`2026-09-29T14:32:52.833453`.

### `GET /api/metrics?window_minutes=60`
`window_minutes` is 1–1440 (default 60).

```json
{
  "window_minutes": 60,
  "units_picked": 42,
  "throughput_per_hour": 42.0,
  "wip": 5,
  "exceptions": 1,
  "workers": {"idle": 3, "busy": 2, "disabled": 1}
}
```

- `units_picked` — sum of `qty` on `task_picked` events in the window
- `throughput_per_hour` — `units_picked × 60 / window_minutes`, one decimal
- `exceptions` — `task_exception` events in the window
- `wip` — tasks whose latest event is `task_assigned` (all time)
- `workers` — `disabled` = not enabled; `idle`/`busy` count enabled workers only

`200` metrics · `422 invalid_window` (out of range) · `422 validation_error` (not an integer).

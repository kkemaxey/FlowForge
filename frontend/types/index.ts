// Shared types that mirror the backend schemas. Add Order, Task and Worker here in Sprint 1.
// Timestamps are UTC ISO 8601 strings with milliseconds, e.g. "2026-11-02T14:03:07.123Z".

export type TaskStatus = "open" | "assigned" | "picked" | "complete" | "exception";

export type WorkerStatus = "idle" | "busy" | "down";

export type ApiErrorBody = { detail: string; code: string };

// modules/simulation/schemas.py
export type ExceptionType = "stockout" | "jam" | "worker_down";

export type ExceptionCreate = { type: ExceptionType; assignment_id: number; qty_found?: number };

export type ExceptionOut = {
  exception_id: number;
  type: ExceptionType;
  task_id: number;
  opened_at: string;
  task_status: TaskStatus;
  rerouted_to_location_id: number | null;
};

export type OpenException = {
  exception_id: number;
  type: ExceptionType;
  task_id: number;
  order_id: number;
  assignment_id: number;
  qty_found: number | null;
  from_location_id: number;
  rerouted_to_location_id: number | null;
  task_status: TaskStatus;
  opened_at: string;
  resolved_at: string | null;
};

// modules/events/schemas.py
export type Throughput = {
  run_id: number;
  window_minutes: number;
  picks: number;
  picks_per_min: number;
  as_of: string;
};

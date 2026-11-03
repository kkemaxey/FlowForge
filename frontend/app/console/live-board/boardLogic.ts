import type { ExceptionType, LiveMetrics, Order, Task, ThroughputBucket } from "./data";

// The live board's calculations, kept apart from the UI in LiveBoard.tsx (per the course engineering
// standards: logic lives in its own layer, and the components only display the results). These are
// plain functions with no React, so they are easy to read and to unit test.

export interface ExceptionAlert {
  taskId: number;
  orderId: number;
  location: string;
  type: ExceptionType;
}

/**
 * Every exception the board should flag, one entry per task.
 * Combines tasks whose status is "exception" with the metrics endpoint's active_exception, so the
 * banner works whichever source the backend fills in first.
 */
export function collectExceptions(tasks: Task[], metrics: LiveMetrics): ExceptionAlert[] {
  const alerts = new Map<number, ExceptionAlert>();
  for (const task of tasks) {
    if (task.status === "exception") {
      alerts.set(task.id, {
        taskId: task.id,
        orderId: task.order_id,
        location: task.location,
        type: task.exception_type ?? "stockout",
      });
    }
  }
  const active = metrics.active_exception;
  if (active && !alerts.has(active.task_id)) {
    alerts.set(active.task_id, {
      taskId: active.task_id,
      orderId: active.order_id,
      location: active.location,
      type: active.type,
    });
  }
  return [...alerts.values()];
}

/** WIP (work in progress) = orders being worked on + tasks handed to workers but not yet picked. */
export function wipTotal(metrics: LiveMetrics): number {
  return metrics.orders_in_progress + metrics.tasks_assigned;
}

/** Orders sorted newest first. Returns a new array so the polled data is never mutated. */
export function sortNewestFirst(orders: Order[]): Order[] {
  return [...orders].sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
}

/**
 * Share of completed orders that finished by their due time, as a whole percent, or null when nothing has
 * completed yet (so the UI can show a dash instead of a misleading 0%).
 */
export function onTimeRate(orders: Order[]): number | null {
  const completed = orders.filter((o) => o.status === "complete" && o.completed_at !== null);
  if (completed.length === 0) return null;
  const onTime = completed.filter((o) => Date.parse(o.completed_at!) <= Date.parse(o.due_at)).length;
  return Math.round((onTime / completed.length) * 100);
}

export interface ThroughputSummary {
  totalUnits: number;
  unitsPerHour: number;
  peak: ThroughputBucket | null;
}

/** Totals for the metrics chart: units in the window, the hourly rate they imply, and the busiest minute. */
export function summarizeThroughput(buckets: ThroughputBucket[]): ThroughputSummary {
  const totalUnits = buckets.reduce((sum, b) => sum + b.units, 0);
  const unitsPerHour = buckets.length === 0 ? 0 : Math.round((totalUnits / buckets.length) * 60);
  const peak = buckets.reduce<ThroughputBucket | null>((best, b) => (best === null || b.units > best.units ? b : best), null);
  return { totalUnits, unitsPerHour, peak };
}

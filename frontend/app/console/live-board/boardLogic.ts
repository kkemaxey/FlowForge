import type { ExceptionType, LiveMetrics, LiveTaskStatus, Order, Task, ThroughputBucket } from "./data";

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
export function collectExceptions(tasks: Task[], metrics: LiveMetrics | null): ExceptionAlert[] {
  const alerts = new Map<number, ExceptionAlert>();
  for (const task of tasks) {
    if (task.status === "exception") {
      alerts.set(task.id, {
        taskId: task.id,
        orderId: task.order_id,
        location: task.location,
        type: task.exception_type ?? "unknown",
      });
    }
  }
  const active = metrics?.active_exception;
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

/** How many tasks are in each status right now. */
export function countTasksByStatus(tasks: Task[]): Record<LiveTaskStatus, number> {
  const counts: Record<LiveTaskStatus, number> = { open: 0, assigned: 0, picked: 0, complete: 0, exception: 0 };
  for (const task of tasks) counts[task.status]++;
  return counts;
}

export interface Wip {
  total: number;
  ordersInProgress: number;
  tasksAssigned: number;
}

/**
 * WIP (work in progress) = orders being worked on (in progress, or late and not yet complete) + tasks handed
 * to workers but not yet picked.
 */
export function workInProgress(orders: Order[], tasks: Task[]): Wip {
  const ordersInProgress = orders.filter((o) => o.status === "in_progress" || o.status === "late").length;
  const tasksAssigned = tasks.filter((t) => t.status === "assigned").length;
  return { total: ordersInProgress + tasksAssigned, ordersInProgress, tasksAssigned };
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
  // An order with no due time can't be late, so it counts as on time.
  const onTime = completed.filter((o) => o.due_at === null || Date.parse(o.completed_at!) <= Date.parse(o.due_at)).length;
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

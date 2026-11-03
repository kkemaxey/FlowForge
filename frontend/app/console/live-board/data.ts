import { apiFetch } from "@/lib/api-client";
import type { TaskStatus } from "@/types";

import { mockMetrics, mockOrders, mockTasks, mockThroughput } from "./mockData";

// Data layer for the live board. Everything the board shows comes through the three getters at the
// bottom of this file. The UI never knows whether it is looking at mock data or the real backend, so
// switching over later only means setting NEXT_PUBLIC_USE_MOCKS=false (no component changes).
// Field names are snake_case so they match the FastAPI JSON with no mapping step (see README.md).

// Order lifecycle as the board sees it. "late" means past due_at and not yet complete.
export type OrderStatus = "new" | "in_progress" | "complete" | "late";

// The shared TaskStatus has no "exception" yet; the live board needs it for the Sprint 2 exception flow.
export type LiveTaskStatus = TaskStatus | "exception";

export type ExceptionType = "stockout" | "worker_down";

// One line item on an order (a SKU and quantity). The backend turns each line into one pick task.
export interface OrderLine {
  id: number;
  order_id: number;
  sku: string;
  quantity: number;
  location: string;
}

// An order as returned by GET /orders, with its lines nested inside.
export interface Order {
  id: number;
  status: OrderStatus;
  created_at: string;
  due_at: string;
  completed_at: string | null;
  lines: OrderLine[];
}

// A pick task as returned by GET /tasks. worker_id is null until the assigner hands it to a worker.
export interface Task {
  id: number;
  order_id: number;
  order_line_id: number;
  sku: string;
  quantity: number;
  location: string;
  status: LiveTaskStatus;
  worker_id: number | null;
  exception_type: ExceptionType | null;
  updated_at: string;
}

// The exception currently blocking work (e.g. a stockout at a location), reported by the metrics endpoint.
export interface ActiveException {
  task_id: number;
  order_id: number;
  location: string;
  type: ExceptionType;
  raised_at: string;
}

// Summary numbers from GET /events/metrics: throughput, WIP pieces, task counts and any active exception.
export interface LiveMetrics {
  units_per_hour: number;
  tasks_per_hour: number;
  orders_in_progress: number;
  tasks_assigned: number;
  task_counts: Record<LiveTaskStatus, number>;
  active_exception: ActiveException | null;
  as_of: string;
}

// One bucket of GET /events/metrics/throughput: what was completed in the minute starting at bucket_start.
export interface ThroughputBucket {
  bucket_start: string;
  units: number;
  tasks: number;
}

// Must be a literal process.env reference so Next.js inlines it at build time.
export const USE_MOCKS = (process.env.NEXT_PUBLIC_USE_MOCKS ?? "true") === "true";

// Each getter returns mock data or calls the backend through the shared apiFetch, which attaches the
// signed-in user's Firebase token. Pass a warehouseId to scope results to one site (?warehouse_id=);
// without one the backend returns everything, which is what the original /console page does.
const scoped = (path: string, warehouseId?: number) =>
  warehouseId === undefined ? path : `${path}${path.includes("?") ? "&" : "?"}warehouse_id=${warehouseId}`;

export function getOrders(warehouseId?: number): Promise<Order[]> {
  return USE_MOCKS ? mockOrders(warehouseId) : apiFetch<Order[]>(scoped("/orders", warehouseId));
}

export function getTasks(warehouseId?: number): Promise<Task[]> {
  return USE_MOCKS ? mockTasks(warehouseId) : apiFetch<Task[]>(scoped("/tasks", warehouseId));
}

export function getMetrics(warehouseId?: number): Promise<LiveMetrics> {
  return USE_MOCKS ? mockMetrics(warehouseId) : apiFetch<LiveMetrics>(scoped("/events/metrics", warehouseId));
}

// Completions per minute over the last `minutes`, oldest first, for the metrics page chart.
export function getThroughput(warehouseId?: number, minutes = 30): Promise<ThroughputBucket[]> {
  return USE_MOCKS
    ? mockThroughput(warehouseId, minutes)
    : apiFetch<ThroughputBucket[]>(scoped(`/events/metrics/throughput?minutes=${minutes}`, warehouseId));
}

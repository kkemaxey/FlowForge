import { apiFetch } from "@/lib/api-client";
import type { TaskStatus, WorkerStatus } from "@/types";

import { mockMetrics, mockOrders, mockTasks } from "./mockData";

// Owner: Jayden
// TODO: move these types into types/index.ts once Kanayo reviews them and the backend schemas exist.
// Field names are snake_case so they match the FastAPI JSON with no mapping step (see README.md).

export type OrderStatus = "new" | "in_progress" | "complete" | "late";

// The shared TaskStatus has no "exception" yet; the live board needs it for the Sprint 2 exception flow.
export type LiveTaskStatus = TaskStatus | "exception";

export type ExceptionType = "stockout" | "worker_down";

export type { WorkerStatus };

export interface OrderLine {
  id: number;
  order_id: number;
  sku: string;
  quantity: number;
  location: string;
}

export interface Order {
  id: number;
  status: OrderStatus;
  created_at: string;
  due_at: string;
  completed_at: string | null;
  lines: OrderLine[];
}

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

export interface ActiveException {
  task_id: number;
  order_id: number;
  location: string;
  type: ExceptionType;
  raised_at: string;
}

export interface LiveMetrics {
  units_per_hour: number;
  tasks_per_hour: number;
  orders_in_progress: number;
  tasks_assigned: number;
  task_counts: Record<LiveTaskStatus, number>;
  active_exception: ActiveException | null;
  as_of: string;
}

// Must be a literal process.env reference so Next.js inlines it at build time.
export const USE_MOCKS = (process.env.NEXT_PUBLIC_USE_MOCKS ?? "true") === "true";

export function getOrders(): Promise<Order[]> {
  return USE_MOCKS ? mockOrders() : apiFetch<Order[]>("/orders");
}

export function getTasks(): Promise<Task[]> {
  return USE_MOCKS ? mockTasks() : apiFetch<Task[]>("/tasks");
}

export function getMetrics(): Promise<LiveMetrics> {
  return USE_MOCKS ? mockMetrics() : apiFetch<LiveMetrics>("/events/metrics");
}

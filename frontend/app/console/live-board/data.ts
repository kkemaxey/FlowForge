import { apiFetch } from "@/lib/api-client";
import type { TaskStatus } from "@/types";

import { mockMetrics, mockOrders, mockTasks, mockThroughput } from "./mockData";

// Data layer for the live board. Everything the board shows comes through the getters at the bottom of
// this file. The UI never knows whether it is looking at mock data or the real backend: with
// NEXT_PUBLIC_USE_MOCKS=false the getters call /api/v1 and map the backend's shapes onto the types below,
// so the components don't change.

// Order lifecycle as the board sees it. "late" means past due_at and not yet complete.
export type OrderStatus = "new" | "in_progress" | "complete" | "late";

// The shared TaskStatus has no "exception" yet; the live board needs it for the exception flow.
export type LiveTaskStatus = TaskStatus | "exception";

export type ExceptionType = "stockout" | "worker_down";

// One line item on an order (a SKU and quantity). The backend turns each line into one or more pick tasks.
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
  due_at: string | null;
  completed_at: string | null;
  lines: OrderLine[];
}

// A pick task. worker_id is null until the assigner hands it to a worker.
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

// Summary numbers from the metrics endpoint. Only throughput and the active exception come from here;
// task counts and WIP are worked out from the tasks themselves (boardLogic.ts).
export interface LiveMetrics {
  units_per_hour: number;
  tasks_per_hour: number;
  active_exception: ActiveException | null;
  as_of: string;
}

// One bucket of the throughput chart: what was completed in the minute starting at bucket_start.
export interface ThroughputBucket {
  bucket_start: string;
  units: number;
  tasks: number;
}

// Must be a literal process.env reference so Next.js inlines it at build time.
export const USE_MOCKS = (process.env.NEXT_PUBLIC_USE_MOCKS ?? "true") === "true";

// ---- Backend shapes (FastAPI, /api/v1) -----------------------------------------------------------------

type ApiTaskStatus = "open" | "assigned" | "picked" | "exception";

interface ApiLocation {
  location_id: number;
  x: number;
  y: number;
  zone: string | null;
  aisle: string | null;
}

interface ApiTask {
  task_id: number;
  order_id: number;
  order_line_id: number;
  sku_code: string;
  qty: number;
  location: ApiLocation;
  status: ApiTaskStatus;
  created_at: string;
  current_assignment: { worker_id: number; assigned_at: string } | null;
}

interface ApiOrder {
  order_id: number;
  status: "open" | "complete";
  due_at: string | null;
  created_at: string;
  lines: {
    order_line_id: number;
    sku_code: string;
    qty_ordered: number;
    tasks: { task_id: number; status: ApiTaskStatus; location: ApiLocation }[];
  }[];
}

// The backend has no bin code, so show the aisle and the cell, e.g. "A3 (7,3)".
const locationLabel = (l: ApiLocation) => `${l.aisle ?? l.zone ?? "?"} (${l.x},${l.y})`;

// "picked" is the backend's final task state, which the board calls "complete".
const taskStatus = (s: ApiTaskStatus): LiveTaskStatus => (s === "picked" ? "complete" : s);

function toTask(t: ApiTask): Task {
  return {
    id: t.task_id,
    order_id: t.order_id,
    order_line_id: t.order_line_id,
    sku: t.sku_code,
    quantity: t.qty,
    location: locationLabel(t.location),
    status: taskStatus(t.status),
    worker_id: t.current_assignment?.worker_id ?? null,
    exception_type: null, // the backend doesn't record the exception type yet
    updated_at: t.current_assignment?.assigned_at ?? t.created_at,
  };
}

// The backend only has open and complete, so the board's in-progress and late come from the tasks and due_at.
function toOrder(o: ApiOrder, now: number): Order {
  const tasks = o.lines.flatMap((line) => line.tasks);
  let status: OrderStatus;
  if (o.status === "complete") status = "complete";
  else if (o.due_at && Date.parse(o.due_at) < now) status = "late";
  else if (tasks.some((t) => t.status !== "open")) status = "in_progress";
  else status = "new";

  return {
    id: o.order_id,
    status,
    created_at: o.created_at,
    due_at: o.due_at,
    completed_at: null, // not in the backend response yet, so on-time % shows a dash
    lines: o.lines.map((line) => ({
      id: line.order_line_id,
      order_id: o.order_id,
      sku: line.sku_code,
      quantity: line.qty_ordered,
      location: line.tasks[0] ? locationLabel(line.tasks[0].location) : "",
    })),
  };
}

const MAX_TASKS = 500; // the backend's limit cap
const MAX_ORDERS = 14; // same table length as the mock board

// getTasks and getOrders both need the task list, and the board calls them together each poll, so a
// request made in the last second is shared instead of sent twice.
let recentTasks: { at: number; request: Promise<ApiTask[]> } | null = null;

function fetchTasks(): Promise<ApiTask[]> {
  const now = Date.now();
  if (!recentTasks || now - recentTasks.at > 1000) {
    const request = apiFetch<{ items: ApiTask[]; count: number }>(`/api/v1/tasks?limit=${MAX_TASKS}`).then((page) => page.items);
    request.catch(() => (recentTasks = null)); // don't share a failed request
    recentTasks = { at: now, request };
  }
  return recentTasks.request;
}

// ---- Getters the board uses ----------------------------------------------------------------------------

export async function getTasks(): Promise<Task[]> {
  return USE_MOCKS ? mockTasks() : (await fetchTasks()).map(toTask);
}

// There is no list endpoint for orders yet, so take the newest order ids from the tasks and fetch each one.
export async function getOrders(): Promise<Order[]> {
  if (USE_MOCKS) return mockOrders();
  const ids = [...new Set((await fetchTasks()).map((t) => t.order_id))].sort((a, b) => b - a).slice(0, MAX_ORDERS);
  const orders = await Promise.all(ids.map((id) => apiFetch<ApiOrder>(`/api/v1/orders/${id}`)));
  const now = Date.now();
  return orders.map((o) => toOrder(o, now));
}

// Optional: the board still works without it. The backend has no metrics endpoint yet, so with real data
// this request fails and the throughput tile shows a dash.
export function getMetrics(): Promise<LiveMetrics> {
  return USE_MOCKS ? mockMetrics() : apiFetch<LiveMetrics>("/api/v1/events/metrics");
}

// Completions per minute over the last `minutes`, oldest first, for the metrics page chart.
export function getThroughput(minutes = 30): Promise<ThroughputBucket[]> {
  return USE_MOCKS
    ? mockThroughput(minutes)
    : apiFetch<ThroughputBucket[]>(`/api/v1/events/metrics/throughput?minutes=${minutes}`);
}

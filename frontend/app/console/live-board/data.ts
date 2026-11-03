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

// "unknown" is used when the backend doesn't say what caused the exception (it doesn't record a type on tasks yet).
export type ExceptionType = "stockout" | "jam" | "worker_down" | "unknown";

// One line item on an order (a SKU and quantity). The backend turns each line into one or more pick tasks.
export interface OrderLine {
  id: number;
  order_id: number;
  sku: string;
  quantity: number;
  location: string; // every bin the line is picked from, e.g. "A2 (4,2), B3 (7,6)" when it is split
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
  updated_at: string | null; // null with real data: the backend doesn't return it yet
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
  completed_at: string | null;
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
    updated_at: null, // the backend has updated_at but doesn't return it; assigned_at would be wrong after a pick
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
    completed_at: o.completed_at,
    lines: o.lines.map((line) => ({
      id: line.order_line_id,
      order_id: o.order_id,
      sku: line.sku_code,
      quantity: line.qty_ordered,
      // A line can be split across bins, so list every distinct location its tasks pick from.
      location: [...new Set(line.tasks.map((t) => locationLabel(t.location)))].join(", "),
    })),
  };
}

const MAX_TASKS = 500; // the backend's limit cap, per status
// On-time % and WIP are worked out from this list, so it needs to span a whole demo, not just the rows
// visible in the table. The seeded stock covers well under 200 orders.
const MAX_ORDERS = 200;
const TASK_STATUSES: ApiTaskStatus[] = ["open", "assigned", "picked", "exception"];

// Fetched one status at a time because GET /tasks sorts oldest first: without a status filter, 500 picked
// tasks would push every new task off the list. Only the picked count can hit the cap, at 500.
async function fetchTasks(): Promise<ApiTask[]> {
  const pages = await Promise.all(
    TASK_STATUSES.map((status) =>
      apiFetch<{ items: ApiTask[]; count: number }>(`/api/v1/tasks?status=${status}&limit=${MAX_TASKS}`),
    ),
  );
  return pages.flatMap((page) => page.items);
}

// ---- Getters the board uses ----------------------------------------------------------------------------

export async function getTasks(): Promise<Task[]> {
  return USE_MOCKS ? mockTasks() : (await fetchTasks()).map(toTask);
}

export async function getOrders(): Promise<Order[]> {
  if (USE_MOCKS) return mockOrders();
  const page = await apiFetch<{ items: ApiOrder[]; count: number }>(`/api/v1/orders?limit=${MAX_ORDERS}`);
  const now = Date.now();
  return page.items.map((o) => toOrder(o, now));
}

// Optional: if this request fails, the rest of the board still updates and the throughput tile shows a dash.
export function getMetrics(): Promise<LiveMetrics> {
  return USE_MOCKS ? mockMetrics() : apiFetch<LiveMetrics>("/api/v1/events/metrics");
}

// Completions per minute over the last `minutes`, oldest first, for the metrics page chart.
export function getThroughput(minutes = 30): Promise<ThroughputBucket[]> {
  return USE_MOCKS
    ? mockThroughput(minutes)
    : apiFetch<ThroughputBucket[]>(`/api/v1/events/metrics/throughput?minutes=${minutes}`);
}

import type { WorkerKind, WorkerStatus } from "@/types";

import { DEMO_SKUS, DEMO_STOCK, DEMO_WAREHOUSE, DEMO_WORKERS } from "./demoWarehouse";

// Mock data for the /concepts pages. Everything is fixed (no Date.now or Math.random) so server and client
// renders match. It describes one moment in sim run #12 on the 10 x 10 demo floor, and reuses the demo
// warehouse's workers, bins and SKUs so the concepts line up with the rest of the portal.

export const SIM_CLOCK = "14:05:00";

const codeAt = new Map(DEMO_WAREHOUSE.locations.map((l) => [`${l.x},${l.y}`, l.code]));
export const binAt = (x: number, y: number) => codeAt.get(`${x},${y}`) ?? `(${x}, ${y})`;
const skuAt = (x: number, y: number) => {
  const stock = DEMO_STOCK.find((s) => s.x === x && s.y === y);
  return stock ? DEMO_SKUS[stock.skuId - 1] : undefined;
};
export const skuNameAt = (x: number, y: number) => skuAt(x, y)?.name ?? "Empty bin";

// ---------------------------------------------------------------- Floor -------------------------------------

export interface ConceptTask {
  id: number;
  orderId: number;
  target: { x: number; y: number };
  sku: string;
  qty: number;
  status: "assigned" | "picked" | "exception";
  etaSec: number | null;
}

export interface ConceptWorker {
  id: number;
  name: string;
  kind: WorkerKind;
  status: WorkerStatus;
  x: number;
  y: number;
  utilization: number; // % of the last hour spent on tasks
  picksLastHour: number;
  battery?: number; // robots only
  task?: ConceptTask;
  note?: string;
}

const task = (id: number, orderId: number, x: number, y: number, qty: number, etaSec: number | null, status: ConceptTask["status"] = "assigned"): ConceptTask => ({
  id,
  orderId,
  target: { x, y },
  sku: skuNameAt(x, y),
  qty,
  status,
  etaSec,
});

const placement: Record<number, Omit<ConceptWorker, "id" | "name" | "kind">> = {
  1: { status: "busy", x: 0, y: 6, utilization: 82, picksLastHour: 41, task: task(331, 1047, 1, 7, 2, 9) },
  2: { status: "busy", x: 3, y: 0, utilization: 91, picksLastHour: 12, note: "Packing order 1044 at station P1" },
  3: { status: "busy", x: 6, y: 3, utilization: 77, picksLastHour: 37, task: task(322, 1045, 5, 2, 1, 6), note: "Auto-reassigned from Morgan" },
  4: { status: "busy", x: 9, y: 7, utilization: 68, picksLastHour: 33, task: task(334, 1048, 8, 5, 1, 4) },
  5: { status: "down", x: 3, y: 4, utilization: 54, picksLastHour: 22, note: "Reported down at 14:03:40" },
  6: { status: "busy", x: 0, y: 2, utilization: 88, picksLastHour: 58, battery: 64, task: task(329, 1046, 1, 1, 3, 3) },
  7: { status: "idle", x: 3, y: 9, utilization: 41, picksLastHour: 27, battery: 92 },
  8: { status: "busy", x: 6, y: 7, utilization: 84, picksLastHour: 55, battery: 47, task: task(333, 1048, 7, 8, 2, 7) },
  9: { status: "offline", x: 9, y: 9, utilization: 0, picksLastHour: 0, battery: 12, note: "Charging, back in about 20 min" },
  10: { status: "busy", x: 3, y: 6, utilization: 73, picksLastHour: 49, battery: 71, task: task(318, 1042, 2, 6, 4, null, "exception"), note: "Waiting on stockout reroute" },
};

export const CONCEPT_WORKERS: ConceptWorker[] = DEMO_WORKERS.map((w) => ({ id: w.id, name: w.name, kind: w.kind, ...placement[w.id] }));

/** Congestion 0..1 on walkable cells, from worker dwell time over the last 5 minutes. */
export const CONGESTION: Record<string, number> = {
  "3,3": 0.55, "3,4": 0.95, "3,5": 0.85, "3,6": 0.9, "3,7": 0.5,
  "6,2": 0.3, "6,3": 0.45, "6,6": 0.35, "6,7": 0.4,
  "0,5": 0.2, "0,6": 0.35, "9,6": 0.25, "9,7": 0.3, "3,0": 0.4, "6,0": 0.2,
};

/** Bins with an open stockout. */
export const STOCKOUT_BINS = [{ x: 2, y: 6 }];

// ---------------------------------------------------------------- KPIs --------------------------------------

export const KPIS = {
  throughput: { value: 1284, target: 1200, trend: [980, 1020, 1110, 1060, 1150, 1210, 1190, 1240, 1300, 1270, 1284] },
  wip: { value: 37, trend: [22, 25, 28, 31, 30, 34, 33, 36, 39, 38, 37] },
  onTime: { value: 94.2, target: 95, trend: [97, 97, 96.5, 96, 96.2, 95.4, 95.1, 94.8, 94.6, 94.4, 94.2] },
  utilization: { value: 73, trend: [61, 64, 66, 70, 72, 71, 74, 75, 73, 74, 73] },
  cycleTime: { value: "4:12", trend: [5.1, 4.9, 4.8, 4.6, 4.5, 4.4, 4.3, 4.3, 4.2, 4.25, 4.2] },
};

// ---------------------------------------------------------------- Orders ------------------------------------

export const PIPELINE = [
  { label: "New", count: 9, tone: "neutral" as const },
  { label: "Assigned", count: 14, tone: "blue" as const },
  { label: "Picking", count: 11, tone: "amber" as const },
  { label: "Packing", count: 3, tone: "violet" as const },
  { label: "Complete", count: 212, tone: "emerald" as const },
];

export interface WatchOrder {
  id: number;
  lines: number;
  picked: number;
  dueIn: string; // "-1:20" when already late
  risk: "late" | "at_risk" | "on_track";
  blocker?: string;
}

export const SLA_WATCHLIST: WatchOrder[] = [
  { id: 1042, lines: 3, picked: 1, dueIn: "-1:20", risk: "late", blocker: `Stockout at ${binAt(2, 6)}` },
  { id: 1045, lines: 2, picked: 1, dueIn: "2:05", risk: "at_risk", blocker: "Worker down, reassigned" },
  { id: 1046, lines: 4, picked: 2, dueIn: "3:40", risk: "at_risk" },
  { id: 1047, lines: 1, picked: 0, dueIn: "6:15", risk: "on_track" },
  { id: 1048, lines: 3, picked: 1, dueIn: "8:50", risk: "on_track" },
];

// ---------------------------------------------------------------- Exceptions --------------------------------

export interface ConceptException {
  id: number;
  type: "stockout" | "worker_down" | "jam";
  title: string;
  where: string;
  taskId: number;
  orderId: number;
  age: string;
  state: "open" | "auto_resolving" | "resolved";
  trail: string[];
  suggestion?: string;
}

export const EXCEPTIONS: ConceptException[] = [
  {
    id: 41,
    type: "stockout",
    title: `Stockout · ${skuNameAt(2, 6)}`,
    where: binAt(2, 6),
    taskId: 318,
    orderId: 1042,
    age: "2m 10s",
    state: "open",
    trail: ["14:02:50 Robo-5 found 0 of 4 pairs", "14:02:51 Task 318 → exception", "14:02:52 Reroute found: same SKU in " + binAt(5, 6)],
    suggestion: `Reroute to ${binAt(5, 6)} (3 pairs) and keep Robo-5`,
  },
  {
    id: 42,
    type: "worker_down",
    title: "Worker down · Morgan",
    where: "(3, 4) aisle A2",
    taskId: 322,
    orderId: 1045,
    age: "1m 20s",
    state: "auto_resolving",
    trail: ["14:03:40 Morgan marked down", "14:03:41 Task 322 released", "14:03:42 Greedy assigner → Jordan (score 0.82)"],
  },
  {
    id: 39,
    type: "jam",
    title: "Jam · station P2",
    where: "(6, 0) station P2",
    taskId: 301,
    orderId: 1038,
    age: "11m",
    state: "resolved",
    trail: ["13:53:10 Jam raised at P2", "13:55:02 Cleared by supervisor"],
  },
];

// ---------------------------------------------------------------- Activity ----------------------------------

export const ACTIVITY = [
  { time: "14:04:58", kind: "pick", text: "Robo-1 picked 3 × Yeezy Boost 350 for order 1046" },
  { time: "14:04:51", kind: "assign", text: "Task 334 → Taylor (greedy_v1, 6 m away)" },
  { time: "14:04:40", kind: "order", text: "Order 1049 received · 2 lines" },
  { time: "14:04:12", kind: "complete", text: "Order 1043 complete · 3:48 cycle time" },
  { time: "14:03:42", kind: "assign", text: "Task 322 auto-reassigned Morgan → Jordan" },
  { time: "14:03:40", kind: "exception", text: "Worker down: Morgan at (3, 4)" },
  { time: "14:02:51", kind: "exception", text: `Stockout at ${binAt(2, 6)} on task 318` },
  { time: "14:02:30", kind: "expedite", text: "Order 1042 expedited by k.maxey" },
] as const;

// ---------------------------------------------------------------- Simulation --------------------------------

export interface SimRun {
  id: number;
  algorithm: string;
  seed: number;
  orderRate: number;
  duration: string;
  orders: number;
  unitsPerHour: number;
  onTime: number;
  avgTravelM: number;
  exceptions: number;
}

export const SIM_RUNS: SimRun[] = [
  { id: 12, algorithm: "greedy_v1", seed: 4821, orderRate: 6, duration: "running", orders: 249, unitsPerHour: 1284, onTime: 94.2, avgTravelM: 11.8, exceptions: 3 },
  { id: 11, algorithm: "greedy_v1", seed: 4821, orderRate: 6, duration: "45:00", orders: 270, unitsPerHour: 1236, onTime: 95.6, avgTravelM: 12.1, exceptions: 2 },
  { id: 10, algorithm: "nearest_v2", seed: 4821, orderRate: 6, duration: "45:00", orders: 270, unitsPerHour: 1342, onTime: 97.1, avgTravelM: 9.4, exceptions: 2 },
  { id: 9, algorithm: "greedy_v1", seed: 77, orderRate: 12, duration: "30:00", orders: 360, unitsPerHour: 1610, onTime: 81.3, avgTravelM: 13.5, exceptions: 6 },
  { id: 8, algorithm: "greedy_v1", seed: 77, orderRate: 3, duration: "30:00", orders: 90, unitsPerHour: 702, onTime: 100, avgTravelM: 10.2, exceptions: 0 },
];

export const OUT_OF_STOCK = [
  { sku: "AJ4-001", name: "Air Jordan 4", rejected: 7 },
  { sku: "PMS-013", name: "Puma Suede", rejected: 2 },
];

// ---------------------------------------------------------------- Backend -----------------------------------

export type ServiceState = "healthy" | "degraded" | "down" | "planned";

export interface ServiceHealth {
  name: string;
  state: ServiceState;
  detail: string;
  metric: string;
  trend: number[];
}

export const SERVICES: ServiceHealth[] = [
  { name: "FastAPI · Cloud Run", state: "healthy", detail: "GET /health 200 · rev flowforge-api-00031", metric: "p95 48 ms", trend: [52, 49, 47, 51, 60, 55, 48, 46, 50, 48] },
  { name: "MySQL · Cloud SQL", state: "healthy", detail: "Pool 4 / 10 in use · Alembic head 0003", metric: "p95 6 ms", trend: [5, 6, 5, 7, 6, 6, 8, 6, 5, 6] },
  { name: "Assigner loop", state: "healthy", detail: "greedy_v1 · ASSIGNER_INTERVAL_SECONDS=2 · last pass 0.4 s ago", metric: "2 conflicts / hr", trend: [0, 1, 0, 0, 2, 1, 0, 0, 1, 0] },
  { name: "Simulator tick", state: "degraded", detail: "Run #12 at 10× · tick 250 ms, running 310 ms", metric: "lag 60 ms", trend: [12, 18, 15, 30, 42, 55, 48, 61, 58, 60] },
  { name: "Order generator", state: "healthy", detail: "6.0 orders/min · seed 4821 · 249 created, 9 rejected", metric: "0 errors", trend: [6, 6, 5, 7, 6, 6, 6, 5, 6, 6] },
  { name: "Firebase Auth", state: "healthy", detail: "Token checks in core/security · 3 sessions today", metric: "0 rejects", trend: [1, 1, 2, 1, 1, 0, 1, 1, 2, 1] },
];

export interface RequestLog {
  time: string;
  requestId: string;
  method: "GET" | "POST" | "PATCH" | "DELETE";
  path: string;
  status: number;
  ms: number;
  user: string;
  code?: string;
}

export const REQUESTS: RequestLog[] = [
  { time: "14:04:59.812", requestId: "a91f3c07b2e4", method: "GET", path: "/api/v1/tasks", status: 200, ms: 38, user: "k.maxey" },
  { time: "14:04:59.640", requestId: "a91f3b5d10c9", method: "GET", path: "/api/v1/generator", status: 200, ms: 9, user: "k.maxey" },
  { time: "14:04:58.002", requestId: "a91f37e2a8f1", method: "POST", path: "/api/v1/assignments/run", status: 200, ms: 112, user: "system" },
  { time: "14:04:51.330", requestId: "a91f22c4d903", method: "POST", path: "/api/v1/tasks/322/reassign", status: 409, ms: 21, user: "j.lee", code: "version_conflict" },
  { time: "14:04:40.118", requestId: "a91f1069be7a", method: "POST", path: "/api/v1/orders", status: 201, ms: 64, user: "generator" },
  { time: "14:04:12.774", requestId: "a91ee8f03c15", method: "PATCH", path: "/api/v1/workers/5", status: 200, ms: 27, user: "t.gaylord" },
  { time: "14:03:58.401", requestId: "a91ed1b7720e", method: "GET", path: "/api/v1/metrics/throughput", status: 404, ms: 4, user: "k.maxey", code: "not_found" },
  { time: "14:03:40.090", requestId: "a91ec08a4d36", method: "POST", path: "/api/v1/tasks/318/exceptions", status: 201, ms: 45, user: "simulator" },
  { time: "14:02:30.555", requestId: "a91e71d2c0bb", method: "POST", path: "/api/v1/orders/1042/expedite", status: 200, ms: 31, user: "k.maxey" },
  { time: "14:01:09.215", requestId: "a91e02f9e641", method: "POST", path: "/api/v1/orders", status: 422, ms: 7, user: "generator", code: "insufficient_stock" },
  { time: "14:00:44.987", requestId: "a91dd93a7c08", method: "GET", path: "/auth/me", status: 200, ms: 18, user: "b.ellis" },
  { time: "13:58:13.004", requestId: "a91d40e15f2a", method: "POST", path: "/api/v1/tasks/315/pick", status: 500, ms: 302, user: "system", code: "internal_error" },
];

export interface Endpoint {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  path: string;
  module: string;
  gate: "public" | "signed in" | "supervisor" | "admin";
  state: "live" | "branch" | "planned";
}

// Live routes are the ones in backend/app/modules/*/router.py on main; "branch" ones are on feature/simulation.
export const ENDPOINTS: Endpoint[] = [
  { method: "GET", path: "/health", module: "core", gate: "public", state: "live" },
  { method: "POST", path: "/auth/session", module: "auth", gate: "signed in", state: "live" },
  { method: "GET", path: "/auth/me", module: "auth", gate: "signed in", state: "live" },
  { method: "POST", path: "/api/v1/orders", module: "orders", gate: "supervisor", state: "live" },
  { method: "GET", path: "/api/v1/orders/{id}", module: "orders", gate: "supervisor", state: "live" },
  { method: "POST", path: "/api/v1/orders/{id}/expedite", module: "orders", gate: "supervisor", state: "live" },
  { method: "GET", path: "/api/v1/tasks", module: "tasks", gate: "supervisor", state: "live" },
  { method: "POST", path: "/api/v1/tasks/{id}/reassign", module: "tasks", gate: "supervisor", state: "live" },
  { method: "POST", path: "/api/v1/assignments/run", module: "assignment", gate: "supervisor", state: "live" },
  { method: "GET", path: "/api/v1/generator", module: "generator", gate: "supervisor", state: "live" },
  { method: "POST", path: "/api/v1/generator/start", module: "generator", gate: "admin", state: "live" },
  { method: "POST", path: "/api/v1/generator/stop", module: "generator", gate: "admin", state: "live" },
  { method: "GET", path: "/api/v1/workers", module: "workforce", gate: "supervisor", state: "live" },
  { method: "POST", path: "/api/v1/workers", module: "workforce", gate: "admin", state: "live" },
  { method: "PATCH", path: "/api/v1/workers/{id}", module: "workforce", gate: "admin", state: "live" },
  { method: "DELETE", path: "/api/v1/workers/{id}", module: "workforce", gate: "admin", state: "live" },
  { method: "GET", path: "/api/v1/exceptions", module: "simulation", gate: "supervisor", state: "branch" },
  { method: "POST", path: "/api/v1/tasks/{id}/exceptions", module: "simulation", gate: "admin", state: "branch" },
  { method: "POST", path: "/api/v1/tasks/{id}/pick", module: "simulation", gate: "supervisor", state: "branch" },
  { method: "GET", path: "/api/v1/simulation/runs/active", module: "simulation", gate: "supervisor", state: "branch" },
  { method: "POST", path: "/api/v1/simulation/runs", module: "simulation", gate: "admin", state: "branch" },
  { method: "GET", path: "/api/v1/metrics/throughput", module: "events", gate: "supervisor", state: "branch" },
  { method: "GET", path: "/api/v1/orders", module: "orders", gate: "supervisor", state: "planned" },
  { method: "PUT", path: "/api/v1/warehouse/layout", module: "warehouse", gate: "admin", state: "planned" },
  { method: "GET", path: "/api/v1/system/health", module: "core", gate: "admin", state: "planned" },
];

export const EVENT_COUNTS = [
  { type: "task_assigned", count: 412 },
  { type: "task_picked", count: 398 },
  { type: "order_created", count: 249 },
  { type: "order_completed", count: 212 },
  { type: "exception_opened", count: 3 },
  { type: "user_login", count: 3 },
];

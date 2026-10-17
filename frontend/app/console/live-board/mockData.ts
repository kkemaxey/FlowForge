import type { ActiveException, LiveMetrics, LiveTaskStatus, Order, Task } from "./data";

// In-browser simulator used while the backend modules are empty (NEXT_PUBLIC_USE_MOCKS=true).
// State advances one tick per TICK_MS of wall time, whenever any getter is called.

const TICK_MS = 1500;
const MAX_CATCH_UP_TICKS = 20;
const THROUGHPUT_WINDOW_MS = 5 * 60_000;
const EXCEPTION_TICKS = 4;
const MAX_ORDERS = 14;

const WORKER_IDS = [1, 2, 3, 4, 5, 6];
const SKUS = ["SKU-1042", "SKU-2210", "SKU-3307", "SKU-4419", "SKU-5523", "SKU-6610", "SKU-7734"];

interface SimState {
  orders: Order[];
  tasks: Task[];
  completions: { at: number; units: number }[];
  exceptionAge: Map<number, number>;
  lastTick: number;
  nextOrderId: number;
  nextLineId: number;
  nextTaskId: number;
}

let sim: SimState | null = null;

const iso = (ms: number) => new Date(ms).toISOString();
const pick = <T>(items: T[]) => items[Math.floor(Math.random() * items.length)];
const randInt = (min: number, max: number) => min + Math.floor(Math.random() * (max - min + 1));
const randomLocation = () =>
  `${pick(["A", "B", "C", "D"])}-${String(randInt(1, 12)).padStart(2, "0")}-${randInt(1, 4)}`;

function addOrder(s: SimState, now: number, dueInMs: number, createdAt = now) {
  const orderId = s.nextOrderId++;
  const order: Order = {
    id: orderId,
    status: "new",
    created_at: iso(createdAt),
    due_at: iso(createdAt + dueInMs),
    completed_at: null,
    lines: [],
  };
  for (let i = randInt(1, 4); i > 0; i--) {
    const line = { id: s.nextLineId++, order_id: orderId, sku: pick(SKUS), quantity: randInt(1, 5), location: randomLocation() };
    order.lines.push(line);
    s.tasks.push({
      id: s.nextTaskId++,
      order_id: orderId,
      order_line_id: line.id,
      sku: line.sku,
      quantity: line.quantity,
      location: line.location,
      status: "open",
      worker_id: null,
      exception_type: null,
      updated_at: iso(createdAt),
    });
  }
  s.orders.push(order);
  return order;
}

function seed(now: number): SimState {
  const s: SimState = {
    orders: [],
    tasks: [],
    completions: [],
    exceptionAge: new Map(),
    lastTick: now,
    nextOrderId: 1001,
    nextLineId: 1,
    nextTaskId: 1,
  };

  // A few orders at different stages, including one already past due.
  const done = addOrder(s, now, 10 * 60_000, now - 4 * 60_000);
  addOrder(s, now, 60_000, now - 3 * 60_000);
  addOrder(s, now, 4 * 60_000, now - 2 * 60_000);
  addOrder(s, now, 3 * 60_000, now - 60_000);
  addOrder(s, now, 2 * 60_000, now - 20_000);

  for (const task of s.tasks) {
    if (task.order_id === done.id) {
      task.status = "complete";
      task.worker_id = pick(WORKER_IDS);
    }
  }
  done.status = "complete";
  done.completed_at = iso(now - 90_000);

  // Backfill completions so throughput isn't zero on first load.
  for (let i = 1; i <= 60; i++) {
    s.completions.push({ at: now - i * 5_000, units: randInt(1, 5) });
  }

  // Run a few ticks so the board opens mid-flow.
  for (let i = 0; i < 4; i++) tick(s, now);
  return s;
}

function tick(s: SimState, now: number) {
  const busy = new Set(s.tasks.filter((t) => t.worker_id !== null && t.status !== "complete" && t.status !== "open").map((t) => t.worker_id));

  // Each task moves at most one step per tick. Iterate a snapshot so newly freed workers wait a tick.
  for (const task of [...s.tasks]) {
    const prev = task.status;
    switch (task.status) {
      case "exception": {
        // Auto-reassignment: after a few ticks the stockout clears and the task goes back to open.
        const age = (s.exceptionAge.get(task.id) ?? 0) + 1;
        if (age >= EXCEPTION_TICKS) {
          s.exceptionAge.delete(task.id);
          task.status = "open";
          task.worker_id = null;
          task.exception_type = null;
        } else {
          s.exceptionAge.set(task.id, age);
        }
        break;
      }
      case "picked":
        if (Math.random() < 0.5) {
          task.status = "complete";
          s.completions.push({ at: now, units: task.quantity });
        }
        break;
      case "assigned":
        if (s.exceptionAge.size === 0 && Math.random() < 0.04) {
          task.status = "exception";
          task.exception_type = "stockout";
          s.exceptionAge.set(task.id, 0);
        } else if (Math.random() < 0.5) {
          task.status = "picked";
        }
        break;
      case "open": {
        const worker = WORKER_IDS.find((id) => !busy.has(id));
        if (worker !== undefined && Math.random() < 0.7) {
          busy.add(worker);
          task.status = "assigned";
          task.worker_id = worker;
        }
        break;
      }
    }
    if (task.status !== prev) task.updated_at = iso(now);
  }

  const openOrders = s.orders.filter((o) => o.status !== "complete").length;
  if (openOrders < 3 || Math.random() < 0.2) {
    // About one in four orders gets a deadline it will likely miss, so late rows show up regularly.
    const dueInSeconds = Math.random() < 0.25 ? randInt(6, 12) : randInt(30, 120);
    addOrder(s, now, dueInSeconds * 1000);
  }

  updateOrderStatuses(s, now);

  // Keep the list short: drop the oldest completed orders and their tasks.
  while (s.orders.length > MAX_ORDERS) {
    const oldest = s.orders.find((o) => o.status === "complete");
    if (!oldest) break;
    s.orders = s.orders.filter((o) => o !== oldest);
    s.tasks = s.tasks.filter((t) => t.order_id !== oldest.id);
  }
  s.completions = s.completions.filter((c) => now - c.at <= THROUGHPUT_WINDOW_MS);
}

function updateOrderStatuses(s: SimState, now: number) {
  for (const order of s.orders) {
    const tasks = s.tasks.filter((t) => t.order_id === order.id);
    if (tasks.every((t) => t.status === "complete")) {
      if (order.status !== "complete") {
        order.status = "complete";
        order.completed_at = iso(now);
      }
    } else if (Date.parse(order.due_at) < now) {
      order.status = "late";
    } else if (tasks.some((t) => t.status !== "open")) {
      order.status = "in_progress";
    } else {
      order.status = "new";
    }
  }
}

function advance(): SimState {
  const now = Date.now();
  if (!sim) sim = seed(now);
  const steps = Math.floor((now - sim.lastTick) / TICK_MS);
  for (let i = 0; i < Math.min(steps, MAX_CATCH_UP_TICKS); i++) {
    tick(sim, now);
  }
  if (steps > 0) sim.lastTick = now;
  return sim;
}

export async function mockOrders(): Promise<Order[]> {
  return structuredClone(advance().orders);
}

export async function mockTasks(): Promise<Task[]> {
  return structuredClone(advance().tasks);
}

export async function mockMetrics(): Promise<LiveMetrics> {
  const s = advance();
  const now = Date.now();
  const perHour = 3_600_000 / THROUGHPUT_WINDOW_MS;
  const recent = s.completions.filter((c) => now - c.at <= THROUGHPUT_WINDOW_MS);

  const task_counts: Record<LiveTaskStatus, number> = { open: 0, assigned: 0, picked: 0, complete: 0, exception: 0 };
  for (const task of s.tasks) task_counts[task.status]++;

  const exceptionTask = s.tasks.find((t) => t.status === "exception");
  const active_exception: ActiveException | null = exceptionTask
    ? {
        task_id: exceptionTask.id,
        order_id: exceptionTask.order_id,
        location: exceptionTask.location,
        type: exceptionTask.exception_type ?? "stockout",
        raised_at: exceptionTask.updated_at,
      }
    : null;

  return {
    units_per_hour: Math.round(recent.reduce((sum, c) => sum + c.units, 0) * perHour),
    tasks_per_hour: Math.round(recent.length * perHour),
    orders_in_progress: s.orders.filter((o) => o.status === "in_progress" || o.status === "late").length,
    tasks_assigned: task_counts.assigned,
    task_counts,
    active_exception,
    as_of: iso(now),
  };
}

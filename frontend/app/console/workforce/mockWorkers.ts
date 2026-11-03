import { ApiRequestError, type ApiFieldError } from "@/lib/api-client";
import { DEMO_WORKERS } from "@/mocks/demoWarehouse";
import type { Worker } from "@/types";

import type { CreateWorkerBody, UpdateWorkerBody, WorkerChanges } from "./data";

// In-browser stand-in for /api/v1/workers, seeded with the demo warehouse's 10 workers. It follows the
// backend's rules (field limits, version compare-and-set, soft delete) and throws the same
// ApiRequestError the real client does, so the UI behaves the same in both modes. State lives in this
// module, so it resets on a full page reload.

const BASE = "/api/v1/workers";
const MOCK_LATENCY_MS = 150;

const seededAt = new Date().toISOString();
const workers: Worker[] = DEMO_WORKERS.map((w) => ({
  worker_id: w.id,
  name: w.name,
  kind: w.kind,
  status: "idle",
  x: w.x,
  y: w.y,
  speed: 1.0,
  is_active: true,
  version: 0,
  created_at: seededAt,
  updated_at: seededAt,
}));
let nextId = Math.max(...workers.map((w) => w.worker_id)) + 1;

const delay = () => new Promise((resolve) => setTimeout(resolve, MOCK_LATENCY_MS));
const copy = (worker: Worker): Worker => ({ ...worker });

function apiError(method: string, path: string, status: number, code: string, detail: string, errors?: ApiFieldError[]) {
  return new ApiRequestError(`${method} ${path} failed: ${status}`, status, { code, detail, errors });
}

// Same limits as the backend's WorkerCreate / WorkerUpdate. Returns the problems found, first field first.
function fieldProblems(fields: WorkerChanges): ApiFieldError[] {
  const problems: ApiFieldError[] = [];
  if (fields.name !== undefined) {
    const name = fields.name.trim();
    if (name.length < 1) problems.push({ loc: ["body", "name"], msg: "String should have at least 1 character" });
    if (name.length > 64) problems.push({ loc: ["body", "name"], msg: "String should have at most 64 characters" });
  }
  if (fields.kind !== undefined && fields.kind !== "human" && fields.kind !== "robot") {
    problems.push({ loc: ["body", "kind"], msg: "Input should be 'human' or 'robot'" });
  }
  for (const axis of ["x", "y"] as const) {
    const value = fields[axis];
    if (value === undefined) continue;
    if (!Number.isInteger(value)) problems.push({ loc: ["body", axis], msg: "Input should be a valid integer" });
    else if (value < 0) problems.push({ loc: ["body", axis], msg: "Input should be greater than or equal to 0" });
  }
  if (fields.speed !== undefined) {
    if (!(fields.speed > 0)) problems.push({ loc: ["body", "speed"], msg: "Input should be greater than 0" });
    else if (fields.speed > 99.99) problems.push({ loc: ["body", "speed"], msg: "Input should be less than or equal to 99.99" });
  }
  return problems;
}

function throwIfInvalid(method: string, path: string, fields: WorkerChanges) {
  const problems = fieldProblems(fields);
  if (problems.length === 0) return;
  const first = problems[0];
  throw apiError(method, path, 422, "validation_error", `${first.loc[first.loc.length - 1]}: ${first.msg}`, problems);
}

function findWorker(method: string, path: string, workerId: number): Worker {
  const worker = workers.find((w) => w.worker_id === workerId);
  if (!worker) throw apiError(method, path, 404, "worker_not_found", `Worker ${workerId} not found`);
  return worker;
}

export async function mockListWorkers(includeInactive: boolean): Promise<Worker[]> {
  await delay();
  return workers.filter((w) => includeInactive || w.is_active).map(copy);
}

export async function mockCreateWorker(body: CreateWorkerBody): Promise<Worker> {
  await delay();
  throwIfInvalid("POST", BASE, body);
  const now = new Date().toISOString();
  const worker: Worker = {
    worker_id: nextId++,
    name: body.name.trim(),
    kind: body.kind,
    status: "idle",
    x: body.x,
    y: body.y,
    speed: body.speed ?? 1.0,
    is_active: true,
    version: 0,
    created_at: now,
    updated_at: now,
  };
  workers.push(worker);
  return copy(worker);
}

export async function mockUpdateWorker(workerId: number, body: UpdateWorkerBody): Promise<Worker> {
  await delay();
  const path = `${BASE}/${workerId}`;
  const { expected_version, ...requested } = body;
  throwIfInvalid("PATCH", path, requested);

  // Same order of checks as the backend: exists, version, active, busy.
  const worker = findWorker("PATCH", path, workerId);
  if (worker.version !== expected_version) {
    throw apiError(
      "PATCH",
      path,
      409,
      "version_conflict",
      `Worker ${workerId} is no longer at version ${expected_version}; reload and retry`,
    );
  }
  if (!worker.is_active) {
    throw apiError("PATCH", path, 409, "worker_inactive", `Worker ${workerId} is deactivated and cannot be edited`);
  }

  if (requested.name !== undefined) requested.name = requested.name.trim();
  const changes = (Object.keys(requested) as (keyof WorkerChanges)[]).filter(
    (field) => requested[field] !== undefined && requested[field] !== worker[field],
  );
  if (changes.length === 0) return copy(worker); // nothing to change: no version bump

  if ((changes.includes("x") || changes.includes("y")) && worker.status === "busy") {
    throw apiError("PATCH", path, 409, "worker_busy", `Worker ${workerId} is busy; it can be moved once it is idle`);
  }

  Object.assign(worker, requested, { version: worker.version + 1, updated_at: new Date().toISOString() });
  return copy(worker);
}

// The mock has no assignments, so worker_has_open_assignment never happens here.
export async function mockDeactivateWorker(workerId: number): Promise<void> {
  await delay();
  const worker = findWorker("DELETE", `${BASE}/${workerId}`, workerId);
  if (!worker.is_active) return; // already deactivated: a no-op, like the backend
  Object.assign(worker, {
    is_active: false,
    status: "offline",
    version: worker.version + 1,
    updated_at: new Date().toISOString(),
  });
}

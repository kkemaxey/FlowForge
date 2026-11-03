import { apiFetch } from "@/lib/api-client";
import type { Worker, WorkerKind, WorkerList } from "@/types";

import { mockCreateWorker, mockDeactivateWorker, mockListWorkers, mockUpdateWorker } from "./mockWorkers";

// Data layer for the workforce page. Components call only the four functions at the bottom, so they
// can't tell mock data from the real /api/v1/workers endpoints: both throw ApiRequestError with the
// backend's error code. Field names are snake_case to match the FastAPI JSON with no mapping step.

// POST /api/v1/workers. speed defaults to 1.0 on the server when left out.
export interface CreateWorkerBody {
  name: string;
  kind: WorkerKind;
  x: number;
  y: number;
  speed?: number;
}

// The editable fields. PATCH sends only the ones that changed.
export type WorkerChanges = Partial<Required<CreateWorkerBody>>;

// PATCH /api/v1/workers/{id}: a compare-and-set on the version the client last saw.
export type UpdateWorkerBody = WorkerChanges & { expected_version: number };

// Must be a literal process.env reference so Next.js inlines it at build time.
export const USE_MOCKS = (process.env.NEXT_PUBLIC_USE_MOCKS ?? "true") === "true";

// The backend's default page is 50; ask for its maximum so a bigger crew isn't cut off silently.
const LIST_LIMIT = 500;

/** Workers ordered by id. Deactivated ones are included only when includeInactive is true. */
export function listWorkers(includeInactive = false): Promise<Worker[]> {
  if (USE_MOCKS) return mockListWorkers(includeInactive);
  return apiFetch<WorkerList>(`/api/v1/workers?include_inactive=${includeInactive}&limit=${LIST_LIMIT}`).then(
    (list) => list.items,
  );
}

export function createWorker(body: CreateWorkerBody): Promise<Worker> {
  if (USE_MOCKS) return mockCreateWorker(body);
  return apiFetch<Worker>("/api/v1/workers", { method: "POST", body: JSON.stringify(body) });
}

export function updateWorker(workerId: number, body: UpdateWorkerBody): Promise<Worker> {
  if (USE_MOCKS) return mockUpdateWorker(workerId, body);
  return apiFetch<Worker>(`/api/v1/workers/${workerId}`, { method: "PATCH", body: JSON.stringify(body) });
}

/** Soft delete: the worker stays in the list (with "Show deactivated") as inactive and offline. */
export function deactivateWorker(workerId: number): Promise<void> {
  if (USE_MOCKS) return mockDeactivateWorker(workerId);
  return apiFetch<void>(`/api/v1/workers/${workerId}`, { method: "DELETE" });
}

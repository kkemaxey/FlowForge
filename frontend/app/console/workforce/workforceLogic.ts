import { ApiRequestError } from "@/lib/api-client";
import type { Worker, WorkerKind } from "@/types";

import type { CreateWorkerBody, WorkerChanges } from "./data";

// The workforce page's rules as plain functions (no React), so they can be read and tested on their own.

export type WorkerField = "name" | "kind" | "x" | "y" | "speed";

// What the add/edit form holds. Numbers stay strings while the user is typing.
export interface WorkerFormValues {
  name: string;
  kind: WorkerKind;
  x: string;
  y: string;
  speed: string;
}

export type WorkerFormErrors = Partial<Record<WorkerField, string>>;

// Mirrors the backend's field rules (backend/app/modules/workforce/schemas.py).
export const NAME_MAX_LENGTH = 64;
export const SPEED_MAX = 99.99;
export const DEFAULT_SPEED = 1.0;

export const EMPTY_FORM: WorkerFormValues = { name: "", kind: "human", x: "0", y: "0", speed: DEFAULT_SPEED.toFixed(1) };

export function formFromWorker(worker: Worker): WorkerFormValues {
  return {
    name: worker.name,
    kind: worker.kind,
    x: String(worker.x),
    y: String(worker.y),
    speed: String(worker.speed),
  };
}

const WHOLE_NUMBER = /^\d+$/;

/** One message per invalid field; an empty object means the form can be sent. */
export function validateWorkerForm(values: WorkerFormValues): WorkerFormErrors {
  const errors: WorkerFormErrors = {};

  const name = values.name.trim();
  if (name.length === 0) errors.name = "Name is required.";
  else if (name.length > NAME_MAX_LENGTH) errors.name = `Name must be ${NAME_MAX_LENGTH} characters or fewer.`;

  if (values.kind !== "human" && values.kind !== "robot") errors.kind = "Choose human or robot.";

  for (const axis of ["x", "y"] as const) {
    const raw = values[axis].trim();
    if (raw === "") errors[axis] = `${axis.toUpperCase()} is required.`;
    else if (!WHOLE_NUMBER.test(raw) || !Number.isSafeInteger(Number(raw)))
      errors[axis] = `${axis.toUpperCase()} must be a whole number, 0 or more.`;
  }

  const speedRaw = values.speed.trim();
  const speed = Number(speedRaw);
  if (speedRaw === "") errors.speed = "Speed is required.";
  else if (!Number.isFinite(speed)) errors.speed = "Speed must be a number.";
  else if (speed <= 0 || speed > SPEED_MAX) errors.speed = `Speed must be more than 0 and at most ${SPEED_MAX}.`;

  return errors;
}

/** The POST body for a validated form. */
export function toCreateBody(values: WorkerFormValues): CreateWorkerBody {
  return {
    name: values.name.trim(),
    kind: values.kind,
    x: Number(values.x),
    y: Number(values.y),
    speed: Number(values.speed),
  };
}

/** The fields of a validated form that differ from the worker as loaded: exactly what PATCH sends. */
export function changedFields(original: Worker, values: WorkerFormValues): WorkerChanges {
  const next = toCreateBody(values);
  const changes: WorkerChanges = {};
  if (next.name !== original.name) changes.name = next.name;
  if (next.kind !== original.kind) changes.kind = next.kind;
  if (next.x !== original.x) changes.x = next.x;
  if (next.y !== original.y) changes.y = next.y;
  if (next.speed !== original.speed) changes.speed = next.speed;
  return changes;
}

const FIELDS: readonly string[] = ["name", "kind", "x", "y", "speed"];

/** The form field a 422 points at (from errors[0].loc, e.g. ["body", "x"]), if it is one of ours. */
export function fieldForError(err: unknown): WorkerField | undefined {
  if (!(err instanceof ApiRequestError) || err.code !== "validation_error") return undefined;
  const loc = err.errors?.[0]?.loc;
  const last = loc?.[loc.length - 1];
  return typeof last === "string" && FIELDS.includes(last) ? (last as WorkerField) : undefined;
}

/** Error codes after which the list on screen is stale and should be reloaded. */
export function shouldReload(err: unknown): boolean {
  return (
    err instanceof ApiRequestError &&
    (err.code === "version_conflict" || err.code === "worker_not_found" || err.code === "worker_inactive")
  );
}

export const GENERIC_ERROR = "Something went wrong talking to the server. Please try again.";

/** Friendly text for an error thrown by the data layer. */
export function messageForError(err: unknown): string {
  if (!(err instanceof ApiRequestError)) return GENERIC_ERROR;
  switch (err.code) {
    case "version_conflict":
      return "Someone else changed this worker. The list has been reloaded; try again.";
    case "worker_busy":
      return "This worker is busy on a task, so it can't be moved until it is idle.";
    case "worker_inactive":
      return "This worker has been deactivated and can't be edited.";
    case "worker_has_open_assignment":
      return "This worker still has an open assignment. Reassign or finish it before deactivating.";
    case "worker_not_found":
      return "This worker no longer exists. The list has been reloaded.";
    case "validation_error":
      return err.detail ?? GENERIC_ERROR;
    default:
      return GENERIC_ERROR;
  }
}

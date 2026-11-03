"use client";

import { useEffect, useId, useState, type FormEvent, type ReactNode } from "react";

import type { Worker, WorkerKind, WorkerStatus } from "@/types";

import { createWorker, deactivateWorker, listWorkers, updateWorker } from "./data";
import {
  changedFields,
  EMPTY_FORM,
  fieldForError,
  formFromWorker,
  messageForError,
  NAME_MAX_LENGTH,
  shouldReload,
  SPEED_MAX,
  toCreateBody,
  validateWorkerForm,
  type WorkerField,
  type WorkerFormErrors,
  type WorkerFormValues,
} from "./workforceLogic";

// Worker list with add, edit and deactivate. A Client Component because it holds form state and calls
// the API from the browser. All rules (validation, what PATCH sends, error text) live in workforceLogic.ts.

const STATUS_BADGE: Record<WorkerStatus, string> = {
  idle: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  busy: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  down: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  offline: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
};

const KIND_LABEL: Record<WorkerKind, string> = { human: "Human", robot: "Robot" };

const BUTTON =
  "rounded-md border border-zinc-300 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800";
const PRIMARY_BUTTON =
  "rounded-md bg-zinc-900 px-3 py-1.5 text-xs font-medium text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300";
const DANGER_BUTTON =
  "rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50";

type FormState = { mode: "create" } | { mode: "edit"; worker: Worker };
type Notice = { tone: "error" | "info"; text: string };

export function WorkforceManager() {
  const [workers, setWorkers] = useState<Worker[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [showInactive, setShowInactive] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  const [form, setForm] = useState<FormState | null>(null);
  const [values, setValues] = useState<WorkerFormValues>(EMPTY_FORM);
  const [fieldErrors, setFieldErrors] = useState<WorkerFormErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const [confirmingId, setConfirmingId] = useState<number | null>(null);
  const [deactivatingId, setDeactivatingId] = useState<number | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);

  // Load (and reload) the list. Late responses are ignored once a newer load has started.
  useEffect(() => {
    let cancelled = false;
    listWorkers(showInactive)
      .then((items) => {
        if (cancelled) return;
        setWorkers(items);
        setLoadError(null);
      })
      .catch((err: unknown) => {
        if (!cancelled) setLoadError(messageForError(err));
      });
    return () => {
      cancelled = true;
    };
  }, [showInactive, reloadKey]);

  const reload = () => setReloadKey((key) => key + 1);

  function openForm(next: FormState) {
    setForm(next);
    setValues(next.mode === "edit" ? formFromWorker(next.worker) : EMPTY_FORM);
    setFieldErrors({});
    setFormError(null);
    setConfirmingId(null);
    setNotice(null);
  }

  function closeForm() {
    setForm(null);
    setFieldErrors({});
    setFormError(null);
  }

  function setField(field: WorkerField, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
    setFieldErrors((current) => ({ ...current, [field]: undefined }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!form) return;

    const errors = validateWorkerForm(values);
    setFieldErrors(errors);
    setFormError(null);
    if (Object.keys(errors).length > 0) return;

    if (form.mode === "edit" && Object.keys(changedFields(form.worker, values)).length === 0) {
      closeForm();
      setNotice({ tone: "info", text: `No changes to save for ${form.worker.name}.` });
      return;
    }

    setSaving(true);
    try {
      if (form.mode === "create") {
        const created = await createWorker(toCreateBody(values));
        setNotice({ tone: "info", text: `Added ${created.name}.` });
      } else {
        const body = { expected_version: form.worker.version, ...changedFields(form.worker, values) };
        const updated = await updateWorker(form.worker.worker_id, body);
        setNotice({ tone: "info", text: `Saved ${updated.name}.` });
      }
      closeForm();
      reload();
    } catch (err) {
      const message = messageForError(err);
      const field = fieldForError(err);
      if (field) setFieldErrors((current) => ({ ...current, [field]: message }));
      else setFormError(message);
      if (shouldReload(err)) {
        // The worker changed under us: close the stale form and show the fresh list.
        closeForm();
        setNotice({ tone: "error", text: message });
        reload();
      }
    } finally {
      setSaving(false);
    }
  }

  async function confirmDeactivate(worker: Worker) {
    setDeactivatingId(worker.worker_id);
    try {
      await deactivateWorker(worker.worker_id);
      setNotice({ tone: "info", text: `Deactivated ${worker.name}.` });
      if (form?.mode === "edit" && form.worker.worker_id === worker.worker_id) closeForm();
      reload();
    } catch (err) {
      setNotice({ tone: "error", text: messageForError(err) });
      if (shouldReload(err)) reload();
    } finally {
      setDeactivatingId(null);
      setConfirmingId(null);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <label className="flex items-center gap-2 text-sm text-zinc-700 dark:text-zinc-300">
          <input
            type="checkbox"
            checked={showInactive}
            onChange={(event) => setShowInactive(event.target.checked)}
            className="h-4 w-4 rounded border-zinc-300 dark:border-zinc-700"
          />
          Show deactivated
        </label>
        <button type="button" className={PRIMARY_BUTTON} onClick={() => openForm({ mode: "create" })} disabled={saving}>
          Add worker
        </button>
      </div>

      {notice && (
        <p
          role={notice.tone === "error" ? "alert" : "status"}
          className={
            notice.tone === "error"
              ? "rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"
              : "rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-700 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-300"
          }
        >
          {notice.text}
        </p>
      )}

      {form && (
        <WorkerForm
          title={form.mode === "create" ? "Add worker" : `Edit ${form.worker.name}`}
          submitLabel={form.mode === "create" ? "Add worker" : "Save changes"}
          values={values}
          errors={fieldErrors}
          formError={formError}
          saving={saving}
          onChange={setField}
          onSubmit={submit}
          onCancel={closeForm}
        />
      )}

      {workers === null && !loadError && <p className="text-sm text-zinc-500">Loading workers…</p>}
      {loadError && (
        <div role="alert" className="flex flex-wrap items-center gap-2 text-sm text-red-600 dark:text-red-400">
          <span>Couldn&apos;t load workers. {loadError}</span>
          <button type="button" className={BUTTON} onClick={reload}>
            Retry
          </button>
        </div>
      )}

      {workers && (
        <WorkerTable
          workers={workers}
          confirmingId={confirmingId}
          deactivatingId={deactivatingId}
          onEdit={(worker) => openForm({ mode: "edit", worker })}
          onAskDeactivate={(worker) => {
            setConfirmingId(worker.worker_id);
            setNotice(null);
          }}
          onCancelDeactivate={() => setConfirmingId(null)}
          onConfirmDeactivate={confirmDeactivate}
        />
      )}
    </div>
  );
}

function WorkerTable({
  workers,
  confirmingId,
  deactivatingId,
  onEdit,
  onAskDeactivate,
  onCancelDeactivate,
  onConfirmDeactivate,
}: {
  workers: Worker[];
  confirmingId: number | null;
  deactivatingId: number | null;
  onEdit: (worker: Worker) => void;
  onAskDeactivate: (worker: Worker) => void;
  onCancelDeactivate: () => void;
  onConfirmDeactivate: (worker: Worker) => void;
}) {
  if (workers.length === 0) return <p className="text-sm text-zinc-500">No workers yet. Add one to get started.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead className="text-xs text-zinc-500">
          <tr className="border-b border-zinc-200 dark:border-zinc-800">
            <th className="py-1.5 pr-3 font-medium">Name</th>
            <th className="py-1.5 pr-3 font-medium">Kind</th>
            <th className="py-1.5 pr-3 font-medium">Status</th>
            <th className="py-1.5 pr-3 font-medium">Position</th>
            <th className="py-1.5 pr-3 text-right font-medium">Speed</th>
            <th className="py-1.5 pr-3 font-medium">Active</th>
            <th className="py-1.5 font-medium">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {workers.map((worker) => {
            const confirming = confirmingId === worker.worker_id;
            const deactivating = deactivatingId === worker.worker_id;
            return (
              <tr
                key={worker.worker_id}
                className={`border-b border-zinc-100 last:border-0 dark:border-zinc-900 ${
                  worker.is_active ? "text-zinc-800 dark:text-zinc-200" : "text-zinc-400 dark:text-zinc-600"
                }`}
              >
                <td className="py-1.5 pr-3 font-medium">{worker.name}</td>
                <td className="py-1.5 pr-3">{KIND_LABEL[worker.kind]}</td>
                <td className="py-1.5 pr-3">
                  <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${STATUS_BADGE[worker.status]}`}>
                    {worker.status}
                  </span>
                </td>
                <td className="py-1.5 pr-3 tabular-nums">
                  ({worker.x}, {worker.y})
                </td>
                <td className="py-1.5 pr-3 text-right tabular-nums">{worker.speed.toFixed(2)}</td>
                <td className="py-1.5 pr-3">{worker.is_active ? "Yes" : "Deactivated"}</td>
                <td className="py-1.5">
                  {confirming ? (
                    <div className="flex flex-wrap items-center justify-end gap-1.5">
                      <span className="text-xs text-zinc-600 dark:text-zinc-400">Deactivate {worker.name}?</span>
                      <button
                        type="button"
                        className={DANGER_BUTTON}
                        onClick={() => onConfirmDeactivate(worker)}
                        disabled={deactivating}
                      >
                        {deactivating ? "Deactivating…" : "Confirm"}
                      </button>
                      <button type="button" className={BUTTON} onClick={onCancelDeactivate} disabled={deactivating}>
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="flex justify-end gap-1.5">
                      <button
                        type="button"
                        className={BUTTON}
                        onClick={() => onEdit(worker)}
                        disabled={!worker.is_active}
                        aria-label={`Edit ${worker.name}`}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className={BUTTON}
                        onClick={() => onAskDeactivate(worker)}
                        disabled={!worker.is_active}
                        aria-label={`Deactivate ${worker.name}`}
                      >
                        Deactivate
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function WorkerForm({
  title,
  submitLabel,
  values,
  errors,
  formError,
  saving,
  onChange,
  onSubmit,
  onCancel,
}: {
  title: string;
  submitLabel: string;
  values: WorkerFormValues;
  errors: WorkerFormErrors;
  formError: string | null;
  saving: boolean;
  onChange: (field: WorkerField, value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
}) {
  const id = useId();
  const input =
    "w-full rounded-md border bg-white px-2 py-1 text-sm text-zinc-900 dark:bg-zinc-900 dark:text-zinc-100 border-zinc-300 dark:border-zinc-700 aria-[invalid=true]:border-red-500";

  return (
    <form
      onSubmit={onSubmit}
      noValidate
      className="flex flex-col gap-3 rounded-md border border-zinc-200 bg-zinc-50 p-3 dark:border-zinc-800 dark:bg-zinc-900/50"
    >
      <h3 className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">{title}</h3>
      <div className="grid gap-3 sm:grid-cols-5">
        <Field id={`${id}-name`} label="Name" error={errors.name}>
          <input
            id={`${id}-name`}
            type="text"
            value={values.name}
            maxLength={NAME_MAX_LENGTH}
            onChange={(event) => onChange("name", event.target.value)}
            aria-invalid={Boolean(errors.name)}
            aria-describedby={errors.name ? `${id}-name-error` : undefined}
            className={input}
          />
        </Field>
        <Field id={`${id}-kind`} label="Kind" error={errors.kind}>
          <select
            id={`${id}-kind`}
            value={values.kind}
            onChange={(event) => onChange("kind", event.target.value)}
            aria-invalid={Boolean(errors.kind)}
            aria-describedby={errors.kind ? `${id}-kind-error` : undefined}
            className={input}
          >
            <option value="human">Human</option>
            <option value="robot">Robot</option>
          </select>
        </Field>
        <Field id={`${id}-speed`} label="Speed" error={errors.speed}>
          <input
            id={`${id}-speed`}
            type="number"
            inputMode="decimal"
            min="0.01"
            max={SPEED_MAX}
            step="0.01"
            value={values.speed}
            onChange={(event) => onChange("speed", event.target.value)}
            aria-invalid={Boolean(errors.speed)}
            aria-describedby={errors.speed ? `${id}-speed-error` : undefined}
            className={input}
          />
        </Field>
        <Field id={`${id}-x`} label="X" error={errors.x}>
          <input
            id={`${id}-x`}
            type="number"
            inputMode="numeric"
            min="0"
            step="1"
            value={values.x}
            onChange={(event) => onChange("x", event.target.value)}
            aria-invalid={Boolean(errors.x)}
            aria-describedby={errors.x ? `${id}-x-error` : undefined}
            className={input}
          />
        </Field>
        <Field id={`${id}-y`} label="Y" error={errors.y}>
          <input
            id={`${id}-y`}
            type="number"
            inputMode="numeric"
            min="0"
            step="1"
            value={values.y}
            onChange={(event) => onChange("y", event.target.value)}
            aria-invalid={Boolean(errors.y)}
            aria-describedby={errors.y ? `${id}-y-error` : undefined}
            className={input}
          />
        </Field>
      </div>
      {formError && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {formError}
        </p>
      )}
      <div className="flex gap-2">
        <button type="submit" className={PRIMARY_BUTTON} disabled={saving}>
          {saving ? "Saving…" : submitLabel}
        </button>
        <button type="button" className={BUTTON} onClick={onCancel} disabled={saving}>
          Cancel
        </button>
      </div>
    </form>
  );
}

function Field({
  id,
  label,
  error,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-zinc-600 dark:text-zinc-400">
        {label}
      </label>
      {children}
      {error && (
        <p id={`${id}-error`} className="text-xs text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}

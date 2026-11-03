"use client";

import { useState } from "react";

import { Badge, BUTTON, DANGER_BUTTON, FIELD, Panel, PRIMARY_BUTTON, Segmented, type Tone } from "@/components/concepts/ConceptKit";
import { CONCEPT_WORKERS, type ConceptWorker, type WorkerEvent } from "@/mocks/conceptMocks";
import { DEMO_HEIGHT, DEMO_WAREHOUSE, DEMO_WIDTH } from "@/mocks/demoWarehouse";

// Workforce, expanded: the same API rules as main (compare-and-set on version, worker_busy, open-assignment
// block on deactivate, worker_* events), plus three proposals from the open steps: auth gates on every route,
// a grid upper bound (422 position_off_grid), and per-worker history read from the events log. Every action
// shows the HTTP exchange it stands for, so the page doubles as a picture of the API.

type Caller = "supervisor" | "unprovisioned" | "none";
type Field = "name" | "speed" | "x" | "y";

const STATUS_TONE: Record<ConceptWorker["status"], Tone> = { idle: "emerald", busy: "blue", down: "red", offline: "neutral" };
const EVENT_TONE: Record<WorkerEvent["type"], string> = {
  worker_created: "text-emerald-700 dark:text-emerald-400",
  worker_updated: "text-blue-700 dark:text-blue-400",
  worker_deactivated: "text-red-700 dark:text-red-400",
  task_assigned: "text-violet-700 dark:text-violet-400",
  task_reassigned: "text-violet-700 dark:text-violet-400",
};

const CELL_CLASS = {
  storage: "bg-blue-300 dark:bg-blue-900",
  aisle: "bg-white dark:bg-zinc-950",
  station: "bg-orange-600 dark:bg-orange-500",
  blocked: "bg-red-100 dark:bg-red-950",
} as const;

interface Exchange {
  request: string;
  status: number;
  body: string;
}

interface Draft {
  name: string;
  kind: "human" | "robot";
  speed: string;
  x: string;
  y: string;
}

const draftOf = (w: ConceptWorker): Draft => ({ name: w.name, kind: w.kind, speed: String(w.speed), x: String(w.x), y: String(w.y) });
const NOW = "Nov 3 14:06:10";

export function WorkforceConcept() {
  const [workers, setWorkers] = useState(CONCEPT_WORKERS);
  const [caller, setCaller] = useState<Caller>("supervisor");
  const [bound, setBound] = useState(true);
  const [showInactive, setShowInactive] = useState(false);
  const [statusFilter, setStatusFilter] = useState<"all" | ConceptWorker["status"]>("all");
  const [selectedId, setSelectedId] = useState(1);
  const [readVersion, setReadVersion] = useState(CONCEPT_WORKERS[0].version);
  const [draft, setDraft] = useState<Draft>(draftOf(CONCEPT_WORKERS[0]));
  const [errors, setErrors] = useState<Partial<Record<Field, string>>>({});
  const [exchange, setExchange] = useState<Exchange | null>(null);
  const [confirming, setConfirming] = useState(false);

  const selected = workers.find((w) => w.id === selectedId)!;
  const rows = workers.filter((w) => (showInactive || w.is_active) && (statusFilter === "all" || w.status === statusFilter));
  const counts = workers.reduce<Record<string, number>>((acc, w) => (w.is_active ? { ...acc, [w.status]: (acc[w.status] ?? 0) + 1 } : acc), {});

  function select(w: ConceptWorker) {
    setSelectedId(w.id);
    setReadVersion(w.version);
    setDraft(draftOf(w));
    setErrors({});
    setConfirming(false);
    setExchange({ request: `GET /api/v1/workers/${w.id}`, ...gateFor(caller) ?? { status: 200, body: JSON.stringify(toOut(w)) } });
  }

  function patchWorker(id: number, fn: (w: ConceptWorker) => ConceptWorker) {
    setWorkers((list) => list.map((w) => (w.id === id ? fn(w) : w)));
  }

  /** Field checks, mirroring workforceLogic.ts plus the proposed grid bound. */
  function validate(d: Draft): Partial<Record<Field, string>> {
    const e: Partial<Record<Field, string>> = {};
    const name = d.name.trim();
    if (!name) e.name = "Name is required.";
    else if (name.length > 64) e.name = "Name must be 64 characters or fewer.";
    const speed = Number(d.speed);
    if (!(speed > 0 && speed <= 99.99)) e.speed = "Speed must be more than 0 and at most 99.99.";
    for (const axis of ["x", "y"] as const) {
      const v = Number(d[axis]);
      const max = axis === "x" ? DEMO_WIDTH - 1 : DEMO_HEIGHT - 1;
      if (!Number.isInteger(v) || v < 0) e[axis] = `${axis} must be a whole number, 0 or more.`;
      else if (bound && v > max) e[axis] = `position_off_grid: ${axis} must be 0–${max} on this ${DEMO_WIDTH} × ${DEMO_HEIGHT} floor.`;
    }
    return e;
  }

  function save() {
    const changes: Record<string, string | number> = {};
    if (draft.name.trim() !== selected.name) changes.name = draft.name.trim();
    if (draft.kind !== selected.kind) changes.kind = draft.kind;
    if (Number(draft.speed) !== selected.speed) changes.speed = Number(draft.speed);
    if (Number(draft.x) !== selected.x) changes.x = Number(draft.x);
    if (Number(draft.y) !== selected.y) changes.y = Number(draft.y);
    const body = JSON.stringify({ expected_version: readVersion, ...changes });
    const request = `PATCH /api/v1/workers/${selected.id}\n${body}`;

    const gate = gateFor(caller);
    if (gate) return setExchange({ request, ...gate });
    const e = validate(draft);
    setErrors(e);
    if (Object.keys(e).length) {
      const off = Object.values(e).find((m) => m?.startsWith("position_off_grid"));
      return setExchange({ request, status: 422, body: JSON.stringify({ detail: off ?? Object.values(e)[0], code: off ? "position_off_grid" : "validation_error" }) });
    }
    if (selected.version !== readVersion)
      return setExchange({
        request,
        status: 409,
        body: JSON.stringify({ detail: `Worker ${selected.id} is no longer at version ${readVersion}; reload and retry`, code: "version_conflict" }),
      });
    if (!selected.is_active)
      return setExchange({ request, status: 409, body: JSON.stringify({ detail: `Worker ${selected.id} is deactivated and cannot be edited`, code: "worker_inactive" }) });
    if (selected.status === "busy" && ("x" in changes || "y" in changes))
      return setExchange({ request, status: 409, body: JSON.stringify({ detail: `Worker ${selected.id} is busy; it can be moved once it is idle`, code: "worker_busy" }) });
    if (!Object.keys(changes).length) return setExchange({ request, status: 200, body: "No changes: same worker back, no version bump, no event." });

    const next: ConceptWorker = {
      ...selected,
      ...(changes as Partial<ConceptWorker>),
      version: selected.version + 1,
      events: [{ at: NOW, type: "worker_updated", text: Object.entries(changes).map(([k, v]) => `${k} → ${v}`).join(", "), by: "you" }, ...selected.events],
    };
    patchWorker(selected.id, () => next);
    setReadVersion(next.version);
    setExchange({ request, status: 200, body: JSON.stringify(toOut(next)) });
  }

  function deactivate() {
    const request = `DELETE /api/v1/workers/${selected.id}`;
    const gate = gateFor(caller);
    setConfirming(false);
    if (gate) return setExchange({ request, ...gate });
    if (!selected.is_active) return setExchange({ request, status: 204, body: "Already deactivated: no-op, no new event." });
    if (selected.openAssignment)
      return setExchange({
        request,
        status: 409,
        body: JSON.stringify({ detail: `Worker ${selected.id} has open assignment ${selected.openAssignment}; reassign or finish it first`, code: "worker_has_open_assignment" }),
      });
    patchWorker(selected.id, (w) => ({
      ...w,
      is_active: false,
      status: "offline",
      version: w.version + 1,
      events: [{ at: NOW, type: "worker_deactivated", text: "Deactivated", by: "you" }, ...w.events],
    }));
    setReadVersion(selected.version + 1);
    setExchange({ request, status: 204, body: "(empty body)" });
  }

  /** Another supervisor edits the same worker: the version moves under the open form. */
  function concurrentEdit() {
    patchWorker(selected.id, (w) => ({
      ...w,
      speed: w.speed === 2 ? 3 : 2,
      version: w.version + 1,
      events: [{ at: NOW, type: "worker_updated", text: `speed ${w.speed} → ${w.speed === 2 ? 3 : 2}`, by: "k.maxey" }, ...w.events],
    }));
  }

  const px = Number(draft.x);
  const py = Number(draft.y);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-zinc-500">Call the API as</span>
          <Segmented
            label="Caller"
            size="xs"
            value={caller}
            onChange={setCaller}
            options={[
              { value: "supervisor", label: "Supervisor" },
              { value: "unprovisioned", label: "Signed in, not provisioned" },
              { value: "none", label: "No token" },
            ]}
          />
          <span className="text-zinc-500">(open step 1: on main every caller gets 200 today)</span>
        </div>
        <label className="flex items-center gap-1.5 text-zinc-700 dark:text-zinc-300">
          <input type="checkbox" checked={bound} onChange={(e) => setBound(e.target.checked)} className="accent-blue-600" />
          Apply the proposed grid bound (open step 6)
        </label>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_26rem]">
        <Panel
          title="Workers"
          subtitle={`${counts.idle ?? 0} idle · ${counts.busy ?? 0} busy · ${counts.down ?? 0} down · GET /api/v1/workers`}
          actions={
            <>
              <Segmented
                label="Status filter"
                size="xs"
                value={statusFilter}
                onChange={setStatusFilter}
                options={[
                  { value: "all", label: "All" },
                  { value: "idle", label: "Idle" },
                  { value: "busy", label: "Busy" },
                  { value: "down", label: "Down" },
                ]}
              />
              <label className="flex items-center gap-1 text-xs text-zinc-600 dark:text-zinc-400">
                <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)} className="accent-blue-600" />
                Show deactivated
              </label>
            </>
          }
        >
          <div className="overflow-x-auto">
            <table className="w-full min-w-[38rem] text-left text-sm">
              <thead className="bg-zinc-50 text-xs text-zinc-500 dark:bg-zinc-900">
                <tr>
                  <th className="px-3 py-2 font-medium">Worker</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Position</th>
                  <th className="px-3 py-2 text-right font-medium">Speed</th>
                  <th className="px-3 py-2 text-right font-medium">Version</th>
                  <th className="px-3 py-2 font-medium">Open assignment</th>
                  <th className="px-3 py-2 font-medium">Last change</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900">
                {rows.map((w) => (
                  <tr
                    key={w.id}
                    onClick={() => select(w)}
                    className={`cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-900 ${w.id === selectedId ? "bg-blue-50 dark:bg-blue-950/40" : ""} ${w.is_active ? "" : "text-zinc-400"}`}
                  >
                    <td className="px-3 py-2">
                      <button type="button" onClick={() => select(w)} className="font-medium underline-offset-2 hover:underline">
                        {w.name}
                      </button>
                      <span className="ml-1.5 text-xs text-zinc-500">
                        #{w.id} · {w.kind}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <Badge tone={STATUS_TONE[w.status]}>{w.status}</Badge>
                    </td>
                    <td className="px-3 py-2 font-mono text-xs">
                      ({w.x}, {w.y})
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">{w.speed}</td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums">{w.version}</td>
                    <td className="px-3 py-2 font-mono text-xs">{w.openAssignment ?? "—"}</td>
                    <td className="px-3 py-2 text-xs text-zinc-500">
                      <span className={EVENT_TONE[w.events[0].type]}>{w.events[0].type}</span> · {w.events[0].by}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-[auto_minmax(0,1fr)]">
            <div>
              <p className="mb-1.5 text-xs font-medium text-zinc-500">Start position · click a cell</p>
              <div
                className="grid w-64 gap-px border border-blue-200 bg-blue-100 dark:border-blue-900 dark:bg-blue-950"
                style={{ gridTemplateColumns: `repeat(${DEMO_WIDTH}, minmax(0, 1fr))`, aspectRatio: "1" }}
              >
                {DEMO_WAREHOUSE.cells.map((type, i) => {
                  const x = i % DEMO_WIDTH;
                  const y = Math.floor(i / DEMO_WIDTH);
                  const here = workers.filter((w) => w.is_active && w.x === x && w.y === y && w.id !== selectedId);
                  const pick = px === x && py === y;
                  return (
                    <button
                      key={i}
                      type="button"
                      aria-label={`(${x}, ${y}) ${type}${here.length ? `, ${here.map((w) => w.name).join(", ")}` : ""}`}
                      title={`(${x}, ${y}) ${type}`}
                      onClick={() => setDraft((d) => ({ ...d, x: String(x), y: String(y) }))}
                      className={`relative ${CELL_CLASS[type]} ${pick ? "z-10 ring-2 ring-blue-600" : ""}`}
                    >
                      {here.length > 0 && <span aria-hidden className="absolute inset-[30%] rounded-full bg-zinc-500/70" />}
                      {pick && <span aria-hidden className="absolute inset-[20%] rounded-full bg-blue-600" />}
                    </button>
                  );
                })}
              </div>
              <p className="mt-1 text-[11px] text-zinc-500">Blue dot: this worker · grey: others</p>
            </div>
            <div className="text-xs text-zinc-600 dark:text-zinc-400">
              <p className="font-medium text-zinc-700 dark:text-zinc-300">Position rules</p>
              <ul className="mt-1 list-disc space-y-0.5 pl-4">
                <li>Main today: x and y are whole numbers, 0 or more. Nothing stops (40, 40) on a 10 × 10 floor.</li>
                <li>
                  Proposed: <span className="font-mono">WAREHOUSE_WIDTH</span> / <span className="font-mono">WAREHOUSE_HEIGHT</span> in core/config.py and a 422{" "}
                  <span className="font-mono">position_off_grid</span>. Type 12 in x with the bound on and off to compare.
                </li>
                <li>Storage cells are allowed (travel is Manhattan, cell types are display-only until pathfinding).</li>
                <li>A busy worker can be renamed but not moved: 409 worker_busy.</li>
              </ul>
            </div>
          </div>
        </Panel>

        <div className="flex flex-col gap-4">
          <Panel
            title={`Edit ${selected.name}`}
            subtitle={`Form read at version ${readVersion} · server has version ${selected.version}`}
            actions={<Badge tone={STATUS_TONE[selected.status]}>{selected.status}</Badge>}
          >
            {selected.version !== readVersion && (
              <p role="status" className="mb-2 rounded-md border border-amber-300 bg-amber-50 px-2 py-1.5 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                Someone changed this worker after you opened it. Saving will return 409 version_conflict.
              </p>
            )}
            <form
              className="grid grid-cols-2 gap-2 text-xs"
              onSubmit={(e) => {
                e.preventDefault();
                save();
              }}
            >
              <label className="col-span-2 flex flex-col gap-1">
                <span className="font-medium text-zinc-600 dark:text-zinc-400">Name</span>
                <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} aria-invalid={!!errors.name} className={FIELD} />
                {errors.name && <span className="text-red-700 dark:text-red-400">{errors.name}</span>}
              </label>
              <label className="flex flex-col gap-1">
                <span className="font-medium text-zinc-600 dark:text-zinc-400">Kind</span>
                <select value={draft.kind} onChange={(e) => setDraft({ ...draft, kind: e.target.value as Draft["kind"] })} className={FIELD}>
                  <option value="human">human</option>
                  <option value="robot">robot</option>
                </select>
              </label>
              <label className="flex flex-col gap-1">
                <span className="font-medium text-zinc-600 dark:text-zinc-400">Speed (cells/s)</span>
                <input value={draft.speed} onChange={(e) => setDraft({ ...draft, speed: e.target.value })} aria-invalid={!!errors.speed} className={FIELD} />
              </label>
              {errors.speed && <span className="col-span-2 text-red-700 dark:text-red-400">{errors.speed}</span>}
              <label className="flex flex-col gap-1">
                <span className="font-medium text-zinc-600 dark:text-zinc-400">x</span>
                <input value={draft.x} onChange={(e) => setDraft({ ...draft, x: e.target.value })} aria-invalid={!!errors.x} className={FIELD} />
              </label>
              <label className="flex flex-col gap-1">
                <span className="font-medium text-zinc-600 dark:text-zinc-400">y</span>
                <input value={draft.y} onChange={(e) => setDraft({ ...draft, y: e.target.value })} aria-invalid={!!errors.y} className={FIELD} />
              </label>
              {(errors.x || errors.y) && <span className="col-span-2 text-red-700 dark:text-red-400">{errors.x ?? errors.y}</span>}
              <div className="col-span-2 mt-1 flex flex-wrap gap-1.5">
                <button type="submit" className={PRIMARY_BUTTON}>
                  Save
                </button>
                <button type="button" className={BUTTON} onClick={() => select(selected)}>
                  Reload
                </button>
                <button type="button" className={BUTTON} onClick={concurrentEdit} title="Simulates another supervisor saving first">
                  Simulate someone else&apos;s edit
                </button>
                {confirming ? (
                  <span className="flex items-center gap-1.5">
                    <button type="button" className={DANGER_BUTTON} onClick={deactivate}>
                      Confirm deactivate
                    </button>
                    <button type="button" className={BUTTON} onClick={() => setConfirming(false)}>
                      Cancel
                    </button>
                  </span>
                ) : (
                  <button type="button" className={BUTTON} onClick={() => setConfirming(true)}>
                    Deactivate…
                  </button>
                )}
              </div>
            </form>
          </Panel>

          <Panel title="Last exchange" subtitle="What the panel sent and what the API answered">
            {exchange ? (
              <div className="flex flex-col gap-2 text-xs">
                <pre className="overflow-x-auto rounded-md bg-zinc-100 p-2 font-mono text-[11px] whitespace-pre-wrap text-zinc-800 dark:bg-zinc-900 dark:text-zinc-200">{exchange.request}</pre>
                <p>
                  <span
                    className={`rounded px-1.5 py-0.5 font-mono font-semibold ${
                      exchange.status >= 400 ? "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300" : "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                    }`}
                  >
                    {exchange.status}
                  </span>
                </p>
                <pre className="overflow-x-auto rounded-md bg-zinc-900 p-2 font-mono text-[11px] whitespace-pre-wrap text-zinc-100">{pretty(exchange.body)}</pre>
              </div>
            ) : (
              <p className="text-xs text-zinc-500">Save, deactivate or pick a worker to see the request and response.</p>
            )}
          </Panel>

          <Panel title="History" subtitle={`events where worker_id = ${selected.id}`}>
            <ol className="flex flex-col gap-1.5 border-l border-zinc-200 pl-3 text-xs dark:border-zinc-800">
              {selected.events.map((e, i) => (
                <li key={i}>
                  <span className="font-mono text-zinc-500">{e.at}</span> <span className={`font-mono font-semibold ${EVENT_TONE[e.type]}`}>{e.type}</span>
                  <span className="block text-zinc-700 dark:text-zinc-300">
                    {e.text} <span className="text-zinc-500">· {e.by}</span>
                  </span>
                </li>
              ))}
            </ol>
            <p className="mt-2 text-[11px] text-zinc-500">Needs GET /api/v1/workers/{"{id}"}/events (new, read-only over the events table).</p>
          </Panel>
        </div>
      </div>
    </div>
  );
}

/** The auth answer for a caller, or null when the call gets through (the proposed gates). */
function gateFor(caller: Caller): Omit<Exchange, "request"> | null {
  if (caller === "none") return { status: 401, body: JSON.stringify({ detail: "Missing bearer token", code: "unauthorized" }) };
  if (caller === "unprovisioned") return { status: 404, body: JSON.stringify({ detail: "User not provisioned; POST /auth/session first", code: "not_provisioned" }) };
  return null;
}

function toOut(w: ConceptWorker) {
  return { worker_id: w.id, name: w.name, kind: w.kind, status: w.status, x: w.x, y: w.y, speed: w.speed, is_active: w.is_active, version: w.version };
}

function pretty(body: string) {
  try {
    return JSON.stringify(JSON.parse(body), null, 2);
  } catch {
    return body;
  }
}

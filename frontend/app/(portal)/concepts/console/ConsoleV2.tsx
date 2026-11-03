"use client";

import Link from "next/link";
import { useState } from "react";

import {
  Badge,
  BUTTON,
  KpiTile,
  Kbd,
  Meter,
  Panel,
  PRIMARY_BUTTON,
  Segmented,
  StatusDot,
  TONE_TEXT,
  type Tone,
} from "@/components/concepts/ConceptKit";
import { FloorLegend, FloorMap, type FloorLayers } from "@/components/concepts/FloorMap";
import {
  ACTIVITY,
  binAt,
  CONCEPT_WORKERS,
  CONGESTION,
  EXCEPTIONS,
  KPIS,
  PIPELINE,
  SIM_CLOCK,
  SLA_WATCHLIST,
  STOCKOUT_BINS,
  type ConceptException,
  type ConceptWorker,
} from "@/mocks/conceptMocks";
import { DEMO_WAREHOUSE } from "@/mocks/demoWarehouse";

// Console v2: one screen a supervisor can run a shift from. Map in the middle, the things that need a
// decision (exceptions, late orders) on the right, and every action one click from where the problem shows.

const STATUS_TONE: Record<ConceptWorker["status"], Tone> = { idle: "emerald", busy: "blue", down: "red", offline: "neutral" };
const EXC_TONE: Record<ConceptException["type"], Tone> = { stockout: "red", worker_down: "orange", jam: "amber" };
const EXC_LABEL: Record<ConceptException["type"], string> = { stockout: "Stockout", worker_down: "Worker down", jam: "Jam" };
const ACTIVITY_TONE: Record<(typeof ACTIVITY)[number]["kind"], Tone> = {
  pick: "blue",
  assign: "violet",
  order: "neutral",
  complete: "emerald",
  exception: "red",
  expedite: "orange",
};

export function ConsoleV2() {
  const [layers, setLayers] = useState<FloorLayers>({ workers: true, paths: true, heat: false, codes: false });
  const [selectedId, setSelectedId] = useState<number | null>(10);
  const [exceptions, setExceptions] = useState(EXCEPTIONS);
  const [excFilter, setExcFilter] = useState<"open" | "all">("open");
  const [expedited, setExpedited] = useState<Set<number>>(new Set([1042]));
  const [toast, setToast] = useState<string | null>(null);

  const selected = CONCEPT_WORKERS.find((w) => w.id === selectedId) ?? null;
  const open = exceptions.filter((e) => e.state !== "resolved");
  const shown = excFilter === "open" ? open : exceptions;

  function act(id: number, text: string) {
    setExceptions((list) => list.map((e) => (e.id === id ? { ...e, state: "resolved", trail: [...e.trail, `${SIM_CLOCK} ${text}`] } : e)));
    setToast(`Exception #${id}: ${text}.`);
  }

  const toggle = (k: keyof FloorLayers) => setLayers((l) => ({ ...l, [k]: !l[k] }));
  const counts = CONCEPT_WORKERS.reduce<Record<string, number>>((acc, w) => ({ ...acc, [w.status]: (acc[w.status] ?? 0) + 1 }), {});

  return (
    <div className="flex flex-col gap-4">
      {/* Run bar: what's running and how fresh the data is, always visible */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-xs dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-zinc-600 dark:text-zinc-400">
          <StatusDot tone="emerald" label="Live · updated 1 s ago" pulse />
          <span>
            Sim run <span className="font-semibold text-zinc-900 dark:text-zinc-100">#12</span>
          </span>
          <span>
            Clock <span className="font-mono font-semibold text-zinc-900 tabular-nums dark:text-zinc-100">{SIM_CLOCK}</span> at{" "}
            <span className="font-semibold">10×</span>
          </span>
          <span>
            Assigner <span className="font-mono">greedy_v1</span>
          </span>
          <span>Generator 6 orders/min</span>
        </div>
        <div className="flex items-center gap-2">
          <button type="button" className={BUTTON}>
            Search orders, tasks, workers <Kbd>⌘K</Kbd>
          </button>
          <Link href="/concepts/simulation" className={BUTTON}>
            Sim controls →
          </Link>
        </div>
      </div>

      {/* KPI row */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
        <KpiTile
          label="Throughput"
          value={KPIS.throughput.value.toLocaleString()}
          unit="units/hr"
          tone="blue"
          trend={KPIS.throughput.trend}
          delta={{ text: "7% vs target", good: true }}
          detail={`Target ${KPIS.throughput.target.toLocaleString()} · last 30 min`}
        />
        <KpiTile label="WIP" value={String(KPIS.wip.value)} tone="orange" trend={KPIS.wip.trend} detail="28 tasks assigned · 9 orders in progress" />
        <KpiTile
          label="On-time"
          value={String(KPIS.onTime.value)}
          unit="%"
          tone="emerald"
          trend={KPIS.onTime.trend}
          delta={{ text: "0.8 pt under", good: false }}
          detail={`Target ${KPIS.onTime.target}% · 1 late, 2 at risk`}
        />
        <KpiTile label="Utilization" value={String(KPIS.utilization.value)} unit="%" tone="violet" trend={KPIS.utilization.trend} detail="Active workers on a task" />
        <KpiTile label="Order cycle time" value={KPIS.cycleTime.value} unit="min" tone="neutral" trend={KPIS.cycleTime.trend} detail="Received → complete, median" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
        {/* Left: map and order flow */}
        <div className="flex min-w-0 flex-col gap-4">
          <Panel
            title="Floor"
            subtitle={`${DEMO_WAREHOUSE.name} · click a worker to inspect`}
            actions={
              <div role="group" aria-label="Map layers" className="flex flex-wrap gap-1">
                {(
                  [
                    ["workers", "Workers"],
                    ["paths", "Paths"],
                    ["heat", "Congestion"],
                    ["codes", "Bin codes"],
                  ] as const
                ).map(([k, label]) => (
                  <button
                    key={k}
                    type="button"
                    aria-pressed={layers[k]}
                    onClick={() => toggle(k)}
                    className={`rounded-md border px-2 py-0.5 text-[11px] font-medium ${
                      layers[k]
                        ? "border-blue-600 bg-blue-50 text-blue-700 dark:border-blue-500 dark:bg-blue-950 dark:text-blue-300"
                        : "border-zinc-300 text-zinc-500 dark:border-zinc-700"
                    }`}
                  >
                    {layers[k] ? "✓ " : ""}
                    {label}
                  </button>
                ))}
              </div>
            }
          >
            <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_15rem]">
              <FloorMap
                warehouse={DEMO_WAREHOUSE}
                workers={CONCEPT_WORKERS}
                congestion={CONGESTION}
                stockouts={STOCKOUT_BINS}
                layers={layers}
                selectedId={selectedId}
                onSelect={setSelectedId}
              />
              <WorkerInspector worker={selected} onClear={() => setSelectedId(null)} />
            </div>
            <div className="mt-3 flex flex-col gap-2 border-t border-zinc-100 pt-3 dark:border-zinc-900">
              <FloorLegend />
              <p className="text-xs text-zinc-500">
                {counts.busy ?? 0} busy · {counts.idle ?? 0} idle · {counts.down ?? 0} down · {counts.offline ?? 0} offline
                {layers.heat && " · Hot spot: aisle column 3, rows 4–6 (Morgan down + Robo-5 waiting). Suggest routing robots via column 0."}
              </p>
            </div>
          </Panel>

          <div className="grid gap-4 lg:grid-cols-2">
            <Panel title="Order flow" subtitle="Where every open order is right now">
              <div className="flex items-stretch gap-1">
                {PIPELINE.map((stage, i) => (
                  <div key={stage.label} className="flex flex-1 items-center gap-1">
                    <div className="flex-1 rounded-md bg-zinc-50 px-1 py-2 text-center dark:bg-zinc-900">
                      <p className={`text-lg font-semibold tabular-nums ${TONE_TEXT[stage.tone]}`}>{stage.count}</p>
                      <p className="text-[11px] text-zinc-500">{stage.label}</p>
                    </div>
                    {i < PIPELINE.length - 1 && (
                      <span aria-hidden className="text-zinc-300 dark:text-zinc-700">
                        ›
                      </span>
                    )}
                  </div>
                ))}
              </div>
              <h3 className="mt-4 mb-1.5 text-xs font-medium text-zinc-500">Worker utilization · last hour</h3>
              <ul className="flex flex-col gap-1.5">
                {[...CONCEPT_WORKERS]
                  .sort((a, b) => b.utilization - a.utilization)
                  .slice(0, 6)
                  .map((w) => (
                    <li key={w.id} className="grid grid-cols-[4.5rem_1fr] items-center gap-2 text-xs">
                      <button type="button" onClick={() => setSelectedId(w.id)} className="truncate text-left text-zinc-700 hover:underline dark:text-zinc-300">
                        {w.name}
                      </button>
                      <Meter value={w.utilization} tone={w.utilization > 85 ? "orange" : "blue"} label={`${w.utilization}%`} />
                    </li>
                  ))}
              </ul>
            </Panel>

            <Panel title="SLA watchlist" subtitle="Late and at-risk orders first" actions={<Badge tone="red">1 late</Badge>}>
              <ul className="flex flex-col divide-y divide-zinc-100 dark:divide-zinc-900">
                {SLA_WATCHLIST.map((o) => {
                  const isExp = expedited.has(o.id);
                  const tone: Tone = o.risk === "late" ? "red" : o.risk === "at_risk" ? "amber" : "emerald";
                  return (
                    <li key={o.id} className={`flex items-center gap-3 py-2 ${o.risk === "late" ? "-mx-2 rounded-md bg-red-50 px-2 dark:bg-red-950/40" : ""}`}>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <Link href={`/orders/${o.id}`} className="font-mono text-sm text-zinc-900 underline underline-offset-2 dark:text-zinc-100">
                            #{o.id}
                          </Link>
                          <Badge tone={tone}>{o.risk === "late" ? "late" : o.risk === "at_risk" ? "at risk" : "on track"}</Badge>
                          {isExp && <Badge tone="orange">↑ expedited</Badge>}
                        </div>
                        <div className="mt-1">
                          <Meter value={o.picked} max={o.lines} tone={tone} label={`${o.picked}/${o.lines}`} />
                        </div>
                        {o.blocker && <p className="mt-0.5 text-[11px] text-zinc-500">{o.blocker}</p>}
                      </div>
                      <div className="w-16 text-right">
                        <p className={`font-mono text-sm tabular-nums ${o.risk === "late" ? "font-semibold text-red-700 dark:text-red-400" : "text-zinc-700 dark:text-zinc-300"}`}>
                          {o.dueIn.startsWith("-") ? `+${o.dueIn.slice(1)}` : o.dueIn}
                        </p>
                        <p className="text-[10px] text-zinc-500">{o.dueIn.startsWith("-") ? "over" : "due in"}</p>
                      </div>
                      <button
                        type="button"
                        disabled={isExp}
                        onClick={() => {
                          setExpedited((s) => new Set(s).add(o.id));
                          setToast(`Order ${o.id} moved to the front of the queue.`);
                        }}
                        className={BUTTON}
                      >
                        Expedite
                      </button>
                    </li>
                  );
                })}
              </ul>
            </Panel>
          </div>
        </div>

        {/* Right rail: decisions, then context */}
        <div className="flex min-w-0 flex-col gap-4">
          <Panel
            title="Needs attention"
            subtitle={`${open.length} open exception${open.length === 1 ? "" : "s"}`}
            actions={
              <Segmented
                label="Exception filter"
                size="xs"
                value={excFilter}
                onChange={setExcFilter}
                options={[
                  { value: "open", label: "Open" },
                  { value: "all", label: "All" },
                ]}
              />
            }
          >
            {shown.length === 0 && <p className="text-sm text-zinc-500">Nothing needs you right now.</p>}
            <ul className="flex flex-col gap-3">
              {shown.map((e) => (
                <li
                  key={e.id}
                  className={`rounded-md border p-3 text-sm ${
                    e.state === "resolved"
                      ? "border-zinc-200 opacity-70 dark:border-zinc-800"
                      : e.state === "open"
                        ? "border-red-300 bg-red-50 dark:border-red-900 dark:bg-red-950/40"
                        : "border-orange-200 bg-orange-50/60 dark:border-orange-900 dark:bg-orange-950/30"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Badge tone={EXC_TONE[e.type]}>{EXC_LABEL[e.type]}</Badge>
                        <span className="text-xs text-zinc-500">#{e.id} · {e.age}</span>
                      </div>
                      <p className="mt-1 font-medium text-zinc-900 dark:text-zinc-100">{e.title}</p>
                      <p className="text-xs text-zinc-600 dark:text-zinc-400">
                        <span className="font-mono">{e.where}</span> · task {e.taskId} · order #{e.orderId}
                      </p>
                    </div>
                    <span className="shrink-0 text-[11px] font-medium text-zinc-500">
                      {e.state === "open" ? "Open" : e.state === "auto_resolving" ? "Auto-fixing" : "Resolved"}
                    </span>
                  </div>
                  <details className="mt-2 text-xs text-zinc-600 dark:text-zinc-400">
                    <summary className="cursor-pointer">Trail ({e.trail.length})</summary>
                    <ol className="mt-1 space-y-0.5 border-l border-zinc-300 pl-2 font-mono text-[11px] dark:border-zinc-700">
                      {e.trail.map((t) => (
                        <li key={t}>{t}</li>
                      ))}
                    </ol>
                  </details>
                  {e.suggestion && e.state === "open" && (
                    <p className="mt-2 rounded bg-white px-2 py-1 text-xs text-zinc-700 dark:bg-zinc-950 dark:text-zinc-300">
                      <span className="font-semibold">Suggested:</span> {e.suggestion}
                    </p>
                  )}
                  {e.state !== "resolved" && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {e.type === "stockout" && (
                        <button type="button" className={PRIMARY_BUTTON} onClick={() => act(e.id, `Rerouted to ${binAt(5, 6)}`)}>
                          Accept reroute
                        </button>
                      )}
                      {e.type === "stockout" && (
                        <button type="button" className={BUTTON} onClick={() => act(e.id, "Marked found, recount queued")}>
                          Stock found
                        </button>
                      )}
                      {e.type === "worker_down" && (
                        <button type="button" className={PRIMARY_BUTTON} onClick={() => act(e.id, "Reassignment confirmed")}>
                          Confirm Jordan
                        </button>
                      )}
                      <button type="button" className={BUTTON} onClick={() => act(e.id, "Acknowledged")}>
                        Acknowledge
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Activity" subtitle="Event log, newest first" actions={<Link href="/concepts/system" className="text-xs text-blue-700 underline dark:text-blue-400">All events</Link>}>
            <ol className="flex flex-col gap-2 text-xs">
              {ACTIVITY.map((a) => (
                <li key={a.time + a.text} className="grid grid-cols-[3.75rem_1fr] gap-2">
                  <span className="font-mono tabular-nums text-zinc-500">{a.time}</span>
                  <span className="text-zinc-700 dark:text-zinc-300">
                    <span className={`mr-1 font-semibold uppercase tracking-wide text-[10px] ${TONE_TEXT[ACTIVITY_TONE[a.kind]]}`}>{a.kind}</span>
                    {a.text}
                  </span>
                </li>
              ))}
            </ol>
          </Panel>
        </div>
      </div>

      {toast && (
        <div role="status" className="fixed right-4 bottom-4 z-10 flex items-center gap-3 rounded-md bg-zinc-900 px-3 py-2 text-sm text-white shadow-lg dark:bg-zinc-100 dark:text-zinc-900">
          {toast}
          <button type="button" className="font-semibold text-blue-300 underline dark:text-blue-700" onClick={() => setToast(null)}>
            Undo
          </button>
          <button type="button" aria-label="Dismiss" className="text-zinc-400" onClick={() => setToast(null)}>
            ✕
          </button>
        </div>
      )}
    </div>
  );
}

function WorkerInspector({ worker, onClear }: { worker: ConceptWorker | null; onClear: () => void }) {
  if (!worker) {
    return (
      <aside className="flex flex-col justify-center rounded-md border border-dashed border-zinc-300 p-3 text-xs text-zinc-500 dark:border-zinc-700">
        Select a worker on the map (or Tab to one and press Enter) to see their task, path and actions.
      </aside>
    );
  }
  const t = worker.task;
  return (
    <aside aria-label={`Worker ${worker.name}`} className="flex flex-col gap-3 rounded-md border border-zinc-200 p-3 text-sm dark:border-zinc-800">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-zinc-900 dark:text-zinc-100">{worker.name}</p>
          <p className="text-xs text-zinc-500">
            {worker.kind === "robot" ? "Robot" : "Human"} · ({worker.x}, {worker.y})
          </p>
        </div>
        <Badge tone={STATUS_TONE[worker.status]}>{worker.status}</Badge>
      </div>
      {worker.note && <p className="rounded bg-zinc-50 px-2 py-1 text-xs text-zinc-600 dark:bg-zinc-900 dark:text-zinc-400">{worker.note}</p>}
      {t ? (
        <dl className="grid grid-cols-[4.5rem_1fr] gap-x-2 gap-y-1 text-xs">
          <dt className="text-zinc-500">Task</dt>
          <dd className="font-mono">
            {t.id} {t.status === "exception" && <span className="font-sans font-semibold text-red-700 dark:text-red-400">· exception</span>}
          </dd>
          <dt className="text-zinc-500">Order</dt>
          <dd className="font-mono">#{t.orderId}</dd>
          <dt className="text-zinc-500">Pick</dt>
          <dd>
            {t.qty} × {t.sku}
          </dd>
          <dt className="text-zinc-500">Bin</dt>
          <dd className="font-mono">{binAt(t.target.x, t.target.y)}</dd>
          <dt className="text-zinc-500">ETA</dt>
          <dd>{t.etaSec === null ? "—" : `${t.etaSec} s`}</dd>
        </dl>
      ) : (
        <p className="text-xs text-zinc-500">No task.</p>
      )}
      <dl className="grid grid-cols-2 gap-2 text-center">
        <div className="rounded bg-zinc-50 py-1.5 dark:bg-zinc-900">
          <dd className="font-semibold tabular-nums">{worker.utilization}%</dd>
          <dt className="text-[10px] text-zinc-500">Utilization</dt>
        </div>
        <div className="rounded bg-zinc-50 py-1.5 dark:bg-zinc-900">
          <dd className="font-semibold tabular-nums">{worker.picksLastHour}</dd>
          <dt className="text-[10px] text-zinc-500">Picks / hr</dt>
        </div>
      </dl>
      {worker.battery !== undefined && (
        <div className="text-xs">
          <p className="mb-1 text-zinc-500">Battery</p>
          <Meter value={worker.battery} tone={worker.battery < 20 ? "red" : worker.battery < 50 ? "amber" : "emerald"} label={`${worker.battery}%`} />
        </div>
      )}
      <div className="mt-auto flex flex-wrap gap-1.5">
        <button type="button" className={BUTTON} disabled={!t}>
          Reassign task
        </button>
        <button type="button" className={BUTTON} disabled={worker.status === "offline"}>
          {worker.status === "down" ? "Mark back up" : "Mark down"}
        </button>
        <button type="button" className={BUTTON} onClick={onClear}>
          Close
        </button>
      </div>
    </aside>
  );
}

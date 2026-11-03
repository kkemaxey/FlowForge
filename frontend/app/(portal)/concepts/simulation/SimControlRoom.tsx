"use client";

import { useState } from "react";

import {
  Badge,
  BUTTON,
  DANGER_BUTTON,
  FIELD,
  Meter,
  Panel,
  PRIMARY_BUTTON,
  Segmented,
  StatusDot,
} from "@/components/concepts/ConceptKit";
import { CONCEPT_WORKERS, OUT_OF_STOCK, SIM_CLOCK, SIM_RUNS, skuNameAt } from "@/mocks/conceptMocks";
import { DEMO_STOCK } from "@/mocks/demoWarehouse";

// Simulation control room (admin). Maps onto what the backend already has: POST /generator/start takes
// order_rate (0 < rate ≤ 600 per minute) and an optional seed, GET /generator reports created / rejected /
// errors / out_of_stock, and POST /assignments/run takes the algorithm name.

type RunState = "running" | "paused" | "stopped";
type Speed = "1" | "10" | "60";
type ExcType = "stockout" | "jam" | "worker_down";

interface Preset {
  name: string;
  blurb: string;
  rate: number;
  speed: Speed;
  seed: number;
}

const PRESETS: Preset[] = [
  { name: "Steady day", blurb: "6 orders/min, 1×. The default demo.", rate: 6, speed: "1", seed: 4821 },
  { name: "Peak rush", blurb: "18 orders/min at 10×. Watch WIP climb.", rate: 18, speed: "10", seed: 77 },
  { name: "Stockout drill", blurb: "Low-stock seed; first stockout in ~2 min.", rate: 8, speed: "10", seed: 9001 },
  { name: "Robot outage", blurb: "Two robots go down at minute 5.", rate: 6, speed: "60", seed: 31337 },
];

interface Injection {
  time: string;
  type: ExcType;
  target: string;
}

export function SimControlRoom() {
  const [state, setState] = useState<RunState>("running");
  const [speed, setSpeed] = useState<Speed>("10");
  const [rate, setRate] = useState(6);
  const [seed, setSeed] = useState("4821");
  const [algorithm, setAlgorithm] = useState("greedy_v1");
  const [confirmReset, setConfirmReset] = useState(false);
  const [resetText, setResetText] = useState("");
  const [preset, setPreset] = useState<string | null>("Steady day");

  const [excType, setExcType] = useState<ExcType>("stockout");
  const [excBin, setExcBin] = useState(DEMO_STOCK[0].code);
  const [excWorker, setExcWorker] = useState(String(CONCEPT_WORKERS[0].id));
  const [qtyFound, setQtyFound] = useState("0");
  const [injections, setInjections] = useState<Injection[]>([{ time: "14:03:40", type: "worker_down", target: "Morgan" }]);

  const [compare, setCompare] = useState<number[]>([11, 10]);

  const seedError = !/^\d+$/.test(seed) || Number(seed) > 2 ** 31 - 1 ? "Seed must be a whole number from 0 to 2,147,483,647." : null;
  const rateError = rate <= 0 || rate > 600 ? "Order rate must be above 0 and at most 600 per minute." : null;

  function applyPreset(p: Preset) {
    setPreset(p.name);
    setRate(p.rate);
    setSpeed(p.speed);
    setSeed(String(p.seed));
  }

  function inject() {
    const target =
      excType === "worker_down"
        ? CONCEPT_WORKERS.find((w) => String(w.id) === excWorker)!.name
        : excType === "stockout"
          ? `${excBin} (found ${qtyFound})`
          : excBin;
    setInjections((list) => [{ time: SIM_CLOCK, type: excType, target }, ...list]);
  }

  const runs = SIM_RUNS.filter((r) => compare.includes(r.id));
  const stateTone = state === "running" ? "emerald" : state === "paused" ? "amber" : "neutral";

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
        <Panel
          title="Run"
          subtitle="Run #12 · started 13:44:10 · 20 min 50 s of sim time"
          actions={<StatusDot tone={stateTone} label={state === "running" ? "Running" : state === "paused" ? "Paused" : "Stopped"} pulse={state === "running"} />}
        >
          <div className="flex flex-wrap items-center gap-2">
            {state !== "running" ? (
              <button type="button" className={PRIMARY_BUTTON} disabled={!!seedError || !!rateError} onClick={() => setState("running")}>
                ▶ {state === "paused" ? "Resume" : "Start new run"}
              </button>
            ) : (
              <button type="button" className={BUTTON} onClick={() => setState("paused")}>
                ❚❚ Pause
              </button>
            )}
            <button type="button" className={BUTTON} disabled={state === "stopped"} onClick={() => setState("stopped")}>
              ■ Stop
            </button>
            <button type="button" className={BUTTON} onClick={() => setConfirmReset(true)}>
              ↺ Reset floor…
            </button>
            <span className="mx-1 h-5 w-px bg-zinc-200 dark:bg-zinc-800" aria-hidden />
            <span className="text-xs text-zinc-500">Speed</span>
            <Segmented
              label="Sim speed"
              value={speed}
              onChange={setSpeed}
              options={[
                { value: "1", label: "1×" },
                { value: "10", label: "10×" },
                { value: "60", label: "60×" },
              ]}
            />
          </div>

          {confirmReset && (
            <div role="alertdialog" aria-label="Confirm reset" className="mt-3 rounded-md border border-red-300 bg-red-50 p-3 text-sm dark:border-red-900 dark:bg-red-950/40">
              <p className="font-medium text-red-900 dark:text-red-200">Reset clears every order, task and assignment for this warehouse.</p>
              <p className="mt-0.5 text-xs text-red-800 dark:text-red-300">
                Workers go back to their start positions and stock is restored. Run #12 is kept in history. Type <span className="font-mono font-semibold">reset</span> to confirm.
              </p>
              <div className="mt-2 flex gap-2">
                <input aria-label="Type reset to confirm" value={resetText} onChange={(e) => setResetText(e.target.value)} className={`${FIELD} w-32`} />
                <button
                  type="button"
                  className={DANGER_BUTTON}
                  disabled={resetText !== "reset"}
                  onClick={() => {
                    setState("stopped");
                    setConfirmReset(false);
                    setResetText("");
                  }}
                >
                  Reset floor
                </button>
                <button type="button" className={BUTTON} onClick={() => setConfirmReset(false)}>
                  Cancel
                </button>
              </div>
            </div>
          )}

          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <label className="flex flex-col gap-1 text-xs text-zinc-600 dark:text-zinc-400">
              <span className="font-medium">
                Order rate · <span className="tabular-nums text-zinc-900 dark:text-zinc-100">{rate}</span> orders/min
              </span>
              <input type="range" min={0.5} max={30} step={0.5} value={rate} onChange={(e) => setRate(Number(e.target.value))} className="accent-blue-600" />
              <span className="flex justify-between text-[10px] text-zinc-400">
                <span>0.5</span>
                <span>30 (API allows up to 600)</span>
              </span>
              {rateError && <span className="text-red-700 dark:text-red-400">{rateError}</span>}
            </label>
            <label className="flex flex-col gap-1 text-xs text-zinc-600 dark:text-zinc-400">
              <span className="font-medium">Seed</span>
              <span className="flex gap-1">
                <input value={seed} onChange={(e) => setSeed(e.target.value)} aria-invalid={!!seedError} className={`${FIELD} w-full font-mono`} />
                <button type="button" className={BUTTON} aria-label="Random seed" onClick={() => setSeed(String((Number(seed || 0) * 48271 + 11) % 2147483647))}>
                  ⚄
                </button>
              </span>
              {seedError ? <span className="text-red-700 dark:text-red-400">{seedError}</span> : <span className="text-[10px] text-zinc-400">Same seed + same algorithm = same orders, for fair comparisons.</span>}
            </label>
            <label className="flex flex-col gap-1 text-xs text-zinc-600 dark:text-zinc-400">
              <span className="font-medium">Assigner</span>
              <select value={algorithm} onChange={(e) => setAlgorithm(e.target.value)} className={FIELD}>
                <option value="greedy_v1">greedy_v1 (baseline)</option>
                <option value="nearest_v2">nearest_v2 (stretch)</option>
                <option value="batch_wave_v1" disabled>
                  batch_wave_v1 (not built)
                </option>
              </select>
              <span className="text-[10px] text-zinc-400">Changing it applies at the next run.</span>
            </label>
          </div>

          <h3 className="mt-5 mb-2 text-xs font-medium text-zinc-500">Scenarios</h3>
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
            {PRESETS.map((p) => (
              <button
                key={p.name}
                type="button"
                aria-pressed={preset === p.name}
                onClick={() => applyPreset(p)}
                className={`rounded-md border p-2.5 text-left text-xs ${
                  preset === p.name
                    ? "border-blue-600 bg-blue-50 dark:border-blue-500 dark:bg-blue-950/50"
                    : "border-zinc-200 hover:border-zinc-300 dark:border-zinc-800 dark:hover:border-zinc-700"
                }`}
              >
                <p className="font-semibold text-zinc-900 dark:text-zinc-100">{p.name}</p>
                <p className="mt-0.5 text-zinc-500">{p.blurb}</p>
                <p className="mt-1 font-mono text-[10px] text-zinc-400">
                  {p.rate}/min · {p.speed}× · seed {p.seed}
                </p>
              </button>
            ))}
          </div>
        </Panel>

        <div className="flex flex-col gap-4">
          <Panel title="Order generator" subtitle="GET /api/v1/generator" actions={<Badge tone="emerald">running</Badge>}>
            <dl className="grid grid-cols-3 gap-2 text-center">
              {[
                ["Created", "249", "text-zinc-900 dark:text-zinc-100"],
                ["Rejected", "9", "text-amber-700 dark:text-amber-400"],
                ["Errors", "0", "text-zinc-900 dark:text-zinc-100"],
              ].map(([label, value, cls]) => (
                <div key={label} className="rounded-md bg-zinc-50 py-2 dark:bg-zinc-900">
                  <dd className={`text-lg font-semibold tabular-nums ${cls}`}>{value}</dd>
                  <dt className="text-[11px] text-zinc-500">{label}</dt>
                </div>
              ))}
            </dl>
            <h3 className="mt-3 mb-1 text-xs font-medium text-zinc-500">Out of stock (orders rejected since)</h3>
            <ul className="flex flex-col gap-1 text-xs">
              {OUT_OF_STOCK.map((s) => (
                <li key={s.sku} className="flex items-center justify-between gap-2">
                  <span>
                    {s.name} <span className="font-mono text-zinc-400">{s.sku}</span>
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="tabular-nums text-amber-700 dark:text-amber-400">{s.rejected}</span>
                    <button type="button" className={BUTTON}>
                      Restock
                    </button>
                  </span>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Inject exception" subtitle="For drills and demos. Logged as source: admin">
            <div className="flex flex-col gap-3 text-xs">
              <Segmented
                label="Exception type"
                value={excType}
                onChange={setExcType}
                options={[
                  { value: "stockout", label: "Stockout" },
                  { value: "jam", label: "Jam" },
                  { value: "worker_down", label: "Worker down" },
                ]}
              />
              {excType === "worker_down" ? (
                <label className="flex flex-col gap-1">
                  <span className="font-medium text-zinc-600 dark:text-zinc-400">Worker</span>
                  <select value={excWorker} onChange={(e) => setExcWorker(e.target.value)} className={`${FIELD} w-full`}>
                    {CONCEPT_WORKERS.filter((w) => w.status !== "offline").map((w) => (
                      <option key={w.id} value={w.id}>
                        {w.name} ({w.kind}, {w.status})
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <div className="grid grid-cols-[minmax(0,1fr)_5rem] gap-2">
                  <label className="flex flex-col gap-1">
                    <span className="font-medium text-zinc-600 dark:text-zinc-400">{excType === "jam" ? "Location" : "Bin"}</span>
                    <select value={excBin} onChange={(e) => setExcBin(e.target.value)} className={`${FIELD} w-full min-w-0`}>
                      {excType === "jam" ? (
                        <>
                          <option value="Station P1">Station P1 (3, 0)</option>
                          <option value="Station P2">Station P2 (6, 0)</option>
                        </>
                      ) : (
                        DEMO_STOCK.map((s) => (
                          <option key={s.code} value={s.code}>
                            {s.code} · {skuNameAt(s.x, s.y)} · {s.pairs} pairs
                          </option>
                        ))
                      )}
                    </select>
                  </label>
                  {excType === "stockout" && (
                    <label className="flex flex-col gap-1">
                      <span className="font-medium text-zinc-600 dark:text-zinc-400">Qty found</span>
                      <input type="number" min={0} value={qtyFound} onChange={(e) => setQtyFound(e.target.value)} className={`${FIELD} w-full`} />
                    </label>
                  )}
                </div>
              )}
              <button type="button" className={`${DANGER_BUTTON} self-start`} disabled={state !== "running"} onClick={inject}>
                Inject {excType.replace("_", " ")}
              </button>
              {state !== "running" && <p className="text-zinc-500">Start or resume the run to inject.</p>}
              <ul className="flex flex-col gap-1 border-t border-zinc-100 pt-2 dark:border-zinc-900">
                {injections.map((i, n) => (
                  <li key={n} className="flex gap-2">
                    <span className="font-mono text-zinc-500">{i.time}</span>
                    <span>
                      {i.type.replace("_", " ")} → {i.target}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </Panel>
        </div>
      </div>

      <Panel title="Run history" subtitle="Tick two runs to compare. Same seed makes the comparison fair.">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[44rem] text-left text-sm">
            <thead className="bg-zinc-50 text-xs text-zinc-500 dark:bg-zinc-900">
              <tr>
                <th className="w-8 px-3 py-2">
                  <span className="sr-only">Compare</span>
                </th>
                <th className="px-3 py-2 font-medium">Run</th>
                <th className="px-3 py-2 font-medium">Assigner</th>
                <th className="px-3 py-2 font-medium">Seed</th>
                <th className="px-3 py-2 text-right font-medium">Rate</th>
                <th className="px-3 py-2 font-medium">Length</th>
                <th className="px-3 py-2 text-right font-medium">Units/hr</th>
                <th className="px-3 py-2 text-right font-medium">On-time</th>
                <th className="px-3 py-2 text-right font-medium">Avg travel</th>
                <th className="px-3 py-2 text-right font-medium">Exceptions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200 tabular-nums dark:divide-zinc-800">
              {SIM_RUNS.map((r) => {
                const checked = compare.includes(r.id);
                return (
                  <tr key={r.id} className={checked ? "bg-blue-50/60 dark:bg-blue-950/30" : undefined}>
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        aria-label={`Compare run ${r.id}`}
                        checked={checked}
                        onChange={() => setCompare((c) => (checked ? c.filter((id) => id !== r.id) : [...c, r.id].slice(-2)))}
                        className="accent-blue-600"
                      />
                    </td>
                    <td className="px-3 py-2 font-mono">#{r.id}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.algorithm}</td>
                    <td className="px-3 py-2 font-mono text-xs">{r.seed}</td>
                    <td className="px-3 py-2 text-right">{r.orderRate}/min</td>
                    <td className="px-3 py-2">{r.duration === "running" ? <Badge tone="emerald">running</Badge> : r.duration}</td>
                    <td className="px-3 py-2 text-right">{r.unitsPerHour.toLocaleString()}</td>
                    <td className={`px-3 py-2 text-right ${r.onTime < 90 ? "font-medium text-red-700 dark:text-red-400" : ""}`}>{r.onTime}%</td>
                    <td className="px-3 py-2 text-right">{r.avgTravelM} m</td>
                    <td className="px-3 py-2 text-right">{r.exceptions}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {runs.length === 2 && <Comparison a={runs[0]} b={runs[1]} />}
      </Panel>
    </div>
  );
}

function Comparison({ a, b }: { a: (typeof SIM_RUNS)[number]; b: (typeof SIM_RUNS)[number] }) {
  const rows: { label: string; key: "unitsPerHour" | "onTime" | "avgTravelM"; unit: string; higherIsBetter: boolean; max: number }[] = [
    { label: "Units/hr", key: "unitsPerHour", unit: "", higherIsBetter: true, max: 1800 },
    { label: "On-time", key: "onTime", unit: "%", higherIsBetter: true, max: 100 },
    { label: "Avg travel", key: "avgTravelM", unit: " m", higherIsBetter: false, max: 15 },
  ];
  const fair = a.seed === b.seed && a.orderRate === b.orderRate;
  return (
    <div className="mt-4 rounded-md border border-zinc-200 p-3 dark:border-zinc-800">
      <p className="text-xs text-zinc-600 dark:text-zinc-400">
        Run <span className="font-mono">#{a.id}</span> ({a.algorithm}) vs <span className="font-mono">#{b.id}</span> ({b.algorithm}){" "}
        {fair ? <Badge tone="emerald">same seed and rate · fair</Badge> : <Badge tone="amber">different seed or rate · not like for like</Badge>}
      </p>
      <div className="mt-3 grid gap-3 md:grid-cols-3">
        {rows.map((row) => {
          const va = a[row.key];
          const vb = b[row.key];
          const better = row.higherIsBetter ? (vb > va ? b : a) : vb < va ? b : a;
          const diff = Math.abs(((vb - va) / va) * 100).toFixed(1);
          return (
            <div key={row.key} className="text-xs">
              <p className="mb-1 font-medium text-zinc-600 dark:text-zinc-400">
                {row.label}{" "}
                <span className="text-emerald-700 dark:text-emerald-400">
                  #{better.id} better by {diff}%
                </span>
              </p>
              {[a, b].map((r) => (
                <div key={r.id} className="grid grid-cols-[2.5rem_1fr] items-center gap-2">
                  <span className="font-mono text-zinc-500">#{r.id}</span>
                  <Meter value={r[row.key]} max={row.max} tone={r.id === better.id ? "emerald" : "neutral"} label={`${r[row.key].toLocaleString()}${row.unit}`} />
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

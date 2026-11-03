"use client";

import { useState } from "react";

import { Badge, BUTTON, FIELD, Meter, Panel, Segmented, Sparkline, StatusDot, type Tone } from "@/components/concepts/ConceptKit";
import { ENDPOINTS, EVENT_COUNTS, REQUESTS, SERVICES, type Endpoint, type RequestLog, type ServiceState } from "@/mocks/conceptMocks";

// Backend console: is the system healthy, what is it doing, and which API routes exist. The request log uses
// the request ids core/request_logging.py already logs on arrival and completion (and echoes as X-Request-ID), so a supervisor's "it failed" can be
// matched to a server log line.

const STATE_TONE: Record<ServiceState, Tone> = { healthy: "emerald", degraded: "amber", down: "red", planned: "neutral" };
const METHOD_TONE: Record<Endpoint["method"], string> = {
  GET: "text-emerald-700 dark:text-emerald-400",
  POST: "text-blue-700 dark:text-blue-400",
  PUT: "text-violet-700 dark:text-violet-400",
  PATCH: "text-amber-700 dark:text-amber-400",
  DELETE: "text-red-700 dark:text-red-400",
};
const GATE_TONE: Record<Endpoint["gate"], Tone> = { public: "neutral", "signed in": "blue", supervisor: "violet", admin: "orange" };
const STATE_BADGE: Record<Endpoint["state"], Tone> = { live: "emerald", branch: "amber", planned: "neutral" };

type StatusFilter = "all" | "2xx" | "4xx" | "5xx";

const statusTone = (s: number) => (s >= 500 ? "text-red-700 dark:text-red-400 font-semibold" : s >= 400 ? "text-amber-700 dark:text-amber-400 font-medium" : "text-zinc-700 dark:text-zinc-300");

export function SystemConsole() {
  const [filter, setFilter] = useState<StatusFilter>("all");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<RequestLog | null>(REQUESTS[3]);
  const [moduleFilter, setModuleFilter] = useState("all");

  const requests = REQUESTS.filter(
    (r) => (filter === "all" || String(r.status)[0] === filter[0]) && (query === "" || `${r.path} ${r.requestId} ${r.user} ${r.code ?? ""}`.includes(query)),
  );
  const modules = ["all", ...new Set(ENDPOINTS.map((e) => e.module))];
  const endpoints = ENDPOINTS.filter((e) => moduleFilter === "all" || e.module === moduleFilter);
  const live = ENDPOINTS.filter((e) => e.state === "live").length;
  const errRate = ((REQUESTS.filter((r) => r.status >= 500).length / REQUESTS.length) * 100).toFixed(1);
  const totalEvents = EVENT_COUNTS.reduce((n, e) => n + e.count, 0);

  return (
    <div className="flex flex-col gap-4">
      {/* Overall verdict first, then the parts */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 dark:border-amber-900 dark:bg-amber-950/40">
        <div>
          <p className="font-semibold text-amber-900 dark:text-amber-200">Degraded: simulator tick is running slow</p>
          <p className="text-xs text-amber-800 dark:text-amber-300">
            Ticks take 310 ms against a 250 ms budget at 10×. Orders still flow; the sim clock drifts about 2 s a minute. Drop to 1× or check Cloud Run CPU.
          </p>
        </div>
        <div className="flex gap-2 text-xs">
          <span className="rounded-md bg-white px-2 py-1 dark:bg-zinc-950">
            5xx <span className="font-semibold tabular-nums">{errRate}%</span> (15 min)
          </span>
          <span className="rounded-md bg-white px-2 py-1 dark:bg-zinc-950">
            Uptime <span className="font-semibold tabular-nums">99.94%</span> (7 d)
          </span>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {SERVICES.map((s) => (
          <div key={s.name} className="flex flex-col gap-1 rounded-md border border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-950">
            <div className="flex items-center justify-between gap-2 text-sm">
              <p className="font-medium text-zinc-900 dark:text-zinc-100">{s.name}</p>
              <span className="text-xs text-zinc-600 dark:text-zinc-400">
                <StatusDot tone={STATE_TONE[s.state]} label={s.state} />
              </span>
            </div>
            <p className="text-xs text-zinc-500">{s.detail}</p>
            <div className="mt-1 flex items-end gap-3">
              <p className="shrink-0 text-sm font-semibold tabular-nums text-zinc-800 dark:text-zinc-200">{s.metric}</p>
              <Sparkline values={s.trend} tone={STATE_TONE[s.state]} className="h-6 w-full" />
            </div>
          </div>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
        <Panel
          title="Request log"
          subtitle="Every API call with its request id · newest first"
          actions={
            <>
              <input placeholder="Filter path, id, user, code" value={query} onChange={(e) => setQuery(e.target.value)} className={`${FIELD} w-48 py-0.5 text-xs`} aria-label="Filter requests" />
              <Segmented
                label="Status"
                size="xs"
                value={filter}
                onChange={setFilter}
                options={[
                  { value: "all", label: "All" },
                  { value: "2xx", label: "2xx" },
                  { value: "4xx", label: "4xx" },
                  { value: "5xx", label: "5xx" },
                ]}
              />
            </>
          }
        >
          <div className="max-h-96 overflow-auto rounded-md border border-zinc-200 dark:border-zinc-800">
            <table className="w-full min-w-[40rem] text-left text-xs">
              <thead className="sticky top-0 bg-zinc-50 text-zinc-500 dark:bg-zinc-900">
                <tr>
                  <th className="px-2 py-1.5 font-medium">Time</th>
                  <th className="px-2 py-1.5 font-medium">Request</th>
                  <th className="px-2 py-1.5 font-medium">Method · path</th>
                  <th className="px-2 py-1.5 text-right font-medium">Status</th>
                  <th className="px-2 py-1.5 text-right font-medium">ms</th>
                  <th className="px-2 py-1.5 font-medium">Caller</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 font-mono tabular-nums dark:divide-zinc-900">
                {requests.map((r) => (
                  <tr
                    key={r.requestId}
                    onClick={() => setOpen(r)}
                    className={`cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-900 ${open?.requestId === r.requestId ? "bg-blue-50 dark:bg-blue-950/40" : ""} ${r.status >= 500 ? "bg-red-50/70 dark:bg-red-950/30" : ""}`}
                  >
                    <td className="px-2 py-1.5 text-zinc-500">{r.time}</td>
                    <td className="px-2 py-1.5">
                      <button type="button" className="underline underline-offset-2" onClick={() => setOpen(r)}>
                        {r.requestId}
                      </button>
                    </td>
                    <td className="px-2 py-1.5">
                      <span className={`font-semibold ${METHOD_TONE[r.method]}`}>{r.method}</span> {r.path}
                    </td>
                    <td className={`px-2 py-1.5 text-right ${statusTone(r.status)}`}>{r.status}</td>
                    <td className={`px-2 py-1.5 text-right ${r.ms > 200 ? "text-amber-700 dark:text-amber-400" : "text-zinc-500"}`}>{r.ms}</td>
                    <td className="px-2 py-1.5 font-sans text-zinc-600 dark:text-zinc-400">{r.user}</td>
                  </tr>
                ))}
                {requests.length === 0 && (
                  <tr>
                    <td colSpan={6} className="px-2 py-4 text-center font-sans text-zinc-500">
                      No requests match.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          {open && (
            <div className="mt-3 rounded-md border border-zinc-200 p-3 text-xs dark:border-zinc-800">
              <div className="flex items-center justify-between">
                <p className="font-semibold text-zinc-800 dark:text-zinc-200">
                  Request <span className="font-mono">{open.requestId}</span>
                </p>
                <button type="button" className={BUTTON} onClick={() => setOpen(null)}>
                  Close
                </button>
              </div>
              <pre className="mt-2 overflow-x-auto rounded bg-zinc-900 p-2 font-mono text-[11px] leading-relaxed text-zinc-100">
                {`${open.time} INFO  request received method=${open.method} path=${open.path} request_id=${open.requestId}
${open.time} ${open.status >= 500 ? "ERROR request failed" : "INFO  request completed"} method=${open.method} path=${open.path}${open.status >= 500 ? "" : ` status=${open.status}`} duration_ms=${open.ms.toFixed(1)} request_id=${open.requestId}${open.code ? `\n# response body: {"detail": "…", "code": "${open.code}"}` : ""}`}
              </pre>
              {open.code === "version_conflict" && (
                <p className="mt-2 text-zinc-600 dark:text-zinc-400">
                  The task changed between the read and the reassign (compare-and-set on <span className="font-mono">expected_version</span>). Expected under load; the console
                  refreshes and asks the user to retry.
                </p>
              )}
              {open.code === "internal_error" && <p className="mt-2 text-red-700 dark:text-red-400">Unhandled exception. Open the Cloud Run log filtered by this request id for the stack trace.</p>}
            </div>
          )}
        </Panel>

        <div className="flex flex-col gap-4">
          <Panel title="Events" subtitle={`${totalEvents.toLocaleString()} written this run`}>
            <ul className="flex flex-col gap-1.5">
              {EVENT_COUNTS.map((e) => (
                <li key={e.type} className="grid grid-cols-[8.5rem_1fr] items-center gap-2 text-xs">
                  <span className="truncate font-mono text-zinc-700 dark:text-zinc-300">{e.type}</span>
                  <Meter value={e.count} max={EVENT_COUNTS[0].count} tone={e.type.startsWith("exception") ? "red" : "blue"} label={String(e.count)} />
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Database">
            <dl className="grid grid-cols-[7rem_1fr] gap-x-2 gap-y-1 text-xs">
              <dt className="text-zinc-500">Engine</dt>
              <dd>MySQL 8 · Cloud SQL</dd>
              <dt className="text-zinc-500">Alembic head</dt>
              <dd className="font-mono break-all">0003_workers_version_updated_at</dd>
              <dt className="text-zinc-500">Pending</dt>
              <dd>
                <Badge tone="emerald">none</Badge>
              </dd>
              <dt className="text-zinc-500">Pool</dt>
              <dd>
                <Meter value={4} max={10} label="4 / 10" />
              </dd>
              <dt className="text-zinc-500">Largest table</dt>
              <dd>events · 18,204 rows</dd>
            </dl>
          </Panel>

          <Panel title="Config" subtitle="Read only. Change through env vars and redeploy.">
            <dl className="grid grid-cols-[11rem_1fr] gap-x-2 gap-y-1 font-mono text-[11px]">
              {[
                ["DATABASE_URL", "mysql+pymysql://•••"],
                ["CORS_ORIGINS", "https://flowforge.vercel.app"],
                ["FIREBASE_CREDENTIALS", "••• (set)"],
                ["ASSIGNER_LOOP_ENABLED", "true"],
                ["ASSIGNER_INTERVAL_SECONDS", "2"],
              ].map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="text-zinc-500">{k}</dt>
                  <dd className="truncate text-zinc-800 dark:text-zinc-200">{v}</dd>
                </div>
              ))}
            </dl>
          </Panel>
        </div>
      </div>

      <Panel
        title="API routes"
        subtitle={`${live} live on main · ${ENDPOINTS.length - live} on branches or planned`}
        actions={
          <select value={moduleFilter} onChange={(e) => setModuleFilter(e.target.value)} className={`${FIELD} py-0.5 text-xs`} aria-label="Module">
            {modules.map((m) => (
              <option key={m} value={m}>
                {m === "all" ? "All modules" : m}
              </option>
            ))}
          </select>
        }
      >
        <div className="overflow-x-auto">
          <table className="w-full min-w-[40rem] text-left text-xs">
            <thead className="text-zinc-500">
              <tr className="border-b border-zinc-200 dark:border-zinc-800">
                <th className="py-1.5 pr-3 font-medium">Route</th>
                <th className="py-1.5 pr-3 font-medium">Module</th>
                <th className="py-1.5 pr-3 font-medium">Proposed gate</th>
                <th className="py-1.5 font-medium">State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900">
              {endpoints.map((e) => (
                <tr key={e.method + e.path}>
                  <td className="py-1.5 pr-3 font-mono">
                    <span className={`inline-block w-12 font-semibold ${METHOD_TONE[e.method]}`}>{e.method}</span>
                    {e.path}
                  </td>
                  <td className="py-1.5 pr-3 font-mono text-zinc-600 dark:text-zinc-400">{e.module}</td>
                  <td className="py-1.5 pr-3">
                    <Badge tone={GATE_TONE[e.gate]}>{e.gate}</Badge>
                  </td>
                  <td className="py-1.5">
                    <Badge tone={STATE_BADGE[e.state]}>{e.state === "branch" ? "on a branch" : e.state}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

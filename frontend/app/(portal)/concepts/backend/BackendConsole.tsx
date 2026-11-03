"use client";

import Link from "next/link";
import { useState } from "react";

import { Badge, BUTTON, Panel, Segmented, type Tone } from "@/components/concepts/ConceptKit";
import {
  CI_JOBS,
  DECISIONS,
  DEPLOY_CHECKLIST,
  ENVS,
  EVENT_COLUMNS,
  EVENT_TYPES,
  OPEN_STEPS,
  ROUTES,
  SUITES,
  type Env,
  type Gate,
  type Route,
  type StepState,
  type Suite,
} from "@/mocks/conceptMocks";

// Backend console scoped to Trent's lane: the open steps first, then one panel per step (route gates, tests
// and CI, deploy, events → metrics, decisions). Each panel shows what main has today next to what's owed, so
// the gap is the thing you read first.

const STEP_TONE: Record<StepState, Tone> = { ready: "blue", blocked: "red", decision: "amber", later: "neutral" };
const STEP_LABEL: Record<StepState, string> = { ready: "Ready to do", blocked: "Blocked", decision: "Needs a decision", later: "Later" };
const GATE_TONE: Record<Gate, Tone> = { public: "neutral", "signed in": "blue", supervisor: "violet" };
const SUITE_TONE: Record<Suite["state"], Tone> = { "on main": "emerald", "on a branch": "amber", "to write": "blue" };
const ENV_TONE: Record<Env["state"], Tone> = { running: "emerald", "not deployed": "neutral", undecided: "amber" };
const METHOD_TONE: Record<Route["method"], string> = {
  GET: "text-emerald-700 dark:text-emerald-400",
  POST: "text-blue-700 dark:text-blue-400",
  PATCH: "text-amber-700 dark:text-amber-400",
  DELETE: "text-red-700 dark:text-red-400",
};

const gap = (r: Route) => r.needs !== "public" && r.today === "none";

export function BackendConsole() {
  const [stepFilter, setStepFilter] = useState<"all" | StepState>("all");
  const [routeScope, setRouteScope] = useState<"mine" | "all">("mine");
  const [gated, setGated] = useState(false);
  const [suiteScope, setSuiteScope] = useState<"mine" | "all">("mine");
  const [checklist, setChecklist] = useState(DEPLOY_CHECKLIST.map((c) => c.done));
  const [decided, setDecided] = useState<Record<string, string>>({});

  const steps = OPEN_STEPS.filter((s) => stepFilter === "all" || s.state === stepFilter);
  const routes = ROUTES.filter((r) => routeScope === "all" || r.mine).map((r) => (gated && r.mine ? { ...r, today: "token" as const, enforced: true } : { ...r, enforced: false }));
  const myGaps = ROUTES.filter((r) => r.mine && gap(r)).length;
  const allGaps = ROUTES.filter(gap).length;
  const suites = SUITES.filter((s) => suiteScope === "all" || s.author === "Trent" || s.state !== "on main");
  const mainTests = SUITES.filter((s) => s.state === "on main").reduce((n, s) => n + (s.tests ?? 0), 0);
  const counts = OPEN_STEPS.reduce<Record<string, number>>((acc, s) => ({ ...acc, [s.state]: (acc[s.state] ?? 0) + 1 }), {});
  const doneCount = checklist.filter(Boolean).length;
  const rejected = EVENT_TYPES.filter((e) => e.onMain && !e.inAllowlist);

  return (
    <div className="flex flex-col gap-4">
      {/* Open steps */}
      <Panel
        title="Open steps"
        subtitle={`${OPEN_STEPS.length} open · ${counts.ready ?? 0} ready · ${counts.blocked ?? 0} blocked · ${counts.decision ?? 0} need a decision · ${counts.later ?? 0} later`}
        actions={
          <Segmented
            label="Filter steps"
            size="xs"
            value={stepFilter}
            onChange={setStepFilter}
            options={[
              { value: "all", label: "All" },
              { value: "ready", label: "Ready" },
              { value: "blocked", label: "Blocked" },
              { value: "decision", label: "Decision" },
              { value: "later", label: "Later" },
            ]}
          />
        }
      >
        <ol className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
          {steps.map((s) => (
            <li key={s.id}>
              <a
                href={`#${s.anchor}`}
                className="flex h-full flex-col gap-1.5 rounded-md border border-zinc-200 p-3 text-sm hover:border-blue-400 dark:border-zinc-800 dark:hover:border-blue-700"
              >
                <span className="flex items-start justify-between gap-2">
                  <span className="font-medium text-zinc-900 dark:text-zinc-100">
                    {OPEN_STEPS.indexOf(s) + 1}. {s.title}
                  </span>
                  <Badge tone={STEP_TONE[s.state]}>{STEP_LABEL[s.state]}</Badge>
                </span>
                <span className="text-xs text-zinc-600 dark:text-zinc-400">{s.detail}</span>
                <span className="mt-auto flex flex-wrap justify-between gap-x-2 text-[11px] text-zinc-500">
                  <span>{s.waitingOn ? `Waiting on ${s.waitingOn}` : "Nothing in the way"}</span>
                  <span>{s.source}</span>
                </span>
              </a>
            </li>
          ))}
        </ol>
      </Panel>

      {/* 1. Route gates */}
      <section id="gates" className="scroll-mt-4">
        <Panel
          title="1 · Route gates"
          subtitle={`What the design doc requires vs what main enforces · ${myGaps} of your ${ROUTES.filter((r) => r.mine).length} routes open · ${allGaps} across the API`}
          actions={
            <>
              <Segmented
                label="Route scope"
                size="xs"
                value={routeScope}
                onChange={setRouteScope}
                options={[
                  { value: "mine", label: "My routes" },
                  { value: "all", label: "Whole API" },
                ]}
              />
              <button type="button" className={BUTTON} aria-pressed={gated} onClick={() => setGated((g) => !g)}>
                {gated ? "↺ Show main today" : "Preview with the change"}
              </button>
            </>
          }
        >
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[36rem] text-left text-xs">
                <thead className="text-zinc-500">
                  <tr className="border-b border-zinc-200 dark:border-zinc-800">
                    <th className="py-1.5 pr-3 font-medium">Route</th>
                    <th className="py-1.5 pr-3 font-medium">Owner</th>
                    <th className="py-1.5 pr-3 font-medium">Needs</th>
                    <th className="py-1.5 pr-3 font-medium">Main today</th>
                    <th className="py-1.5 font-medium">Unauthenticated call</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900">
                  {routes.map((r) => {
                    const open = gap(r);
                    return (
                      <tr key={r.method + r.path} className={open && r.mine ? "bg-red-50/60 dark:bg-red-950/20" : undefined}>
                        <td className="py-1.5 pr-3 font-mono">
                          <span className={`inline-block w-14 font-semibold ${METHOD_TONE[r.method]}`}>{r.method}</span>
                          {r.path}
                        </td>
                        <td className="py-1.5 pr-3">{r.mine ? <Badge tone="blue">you</Badge> : <span className="text-zinc-600 dark:text-zinc-400">{r.owner}</span>}</td>
                        <td className="py-1.5 pr-3">
                          <Badge tone={GATE_TONE[r.needs]}>{r.needs}</Badge>
                        </td>
                        <td className="py-1.5 pr-3">
                          {r.enforced ? (
                            <span className="font-medium text-emerald-700 dark:text-emerald-400">{r.needs === "supervisor" ? "require_supervisor" : "current_app_user"}</span>
                          ) : r.today === "token" ? (
                            <span className="text-zinc-700 dark:text-zinc-300">Firebase token</span>
                          ) : r.needs === "public" ? (
                            <span className="text-zinc-500">open (correct)</span>
                          ) : (
                            <span className="font-medium text-red-700 dark:text-red-400">no check</span>
                          )}
                        </td>
                        <td className="py-1.5 font-mono">
                          {r.needs === "public" ? "200" : open ? <span className="font-semibold text-red-700 dark:text-red-400">200 ✗</span> : <span className="text-emerald-700 dark:text-emerald-400">401 ✓</span>}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <div className="flex flex-col gap-2 text-xs">
              <p className="font-medium text-zinc-700 dark:text-zinc-300">The change, in workforce/router.py</p>
              <pre className="overflow-x-auto rounded-md bg-zinc-900 p-3 font-mono text-[11px] leading-relaxed text-zinc-100">
                {`from app.modules.auth.service import (
    current_app_user, require_supervisor,
)

router = APIRouter(
    prefix="/api/v1/workers",
    tags=["workforce"],
    dependencies=[Depends(current_app_user)],
)

@router.post("", ...,
    dependencies=[Depends(require_supervisor)])
# same on PATCH and DELETE`}
              </pre>
              <ul className="list-disc space-y-0.5 pl-4 text-zinc-600 dark:text-zinc-400">
                <li>No token → 401. Signed in, not provisioned → 404 not_provisioned. Not a supervisor → 403.</li>
                <li>Tests: add a test_workforce_auth.py and give the existing suites a supervisor override of the dependency.</li>
                <li>The frontend panel already sends the token through apiFetch, so the UI won&apos;t need changes.</li>
              </ul>
            </div>
          </div>
        </Panel>
      </section>

      {/* 2–3. Tests and CI */}
      <section id="tests" className="scroll-mt-4">
        <Panel
          title="2–3 · Tests and CI"
          subtitle={`${mainTests} test functions on main · 6 suites waiting on feature/simulation · 1 to write`}
          actions={
            <Segmented
              label="Suite scope"
              size="xs"
              value={suiteScope}
              onChange={setSuiteScope}
              options={[
                { value: "mine", label: "Yours + gaps" },
                { value: "all", label: "Every suite" },
              ]}
            />
          }
        >
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1fr)_24rem]">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[34rem] text-left text-xs">
                <thead className="text-zinc-500">
                  <tr className="border-b border-zinc-200 dark:border-zinc-800">
                    <th className="py-1.5 pr-3 font-medium">Suite</th>
                    <th className="py-1.5 pr-3 font-medium">Covers</th>
                    <th className="py-1.5 pr-3 font-medium">Author</th>
                    <th className="py-1.5 pr-3 text-right font-medium">Tests</th>
                    <th className="py-1.5 font-medium">State</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900">
                  {suites.map((s) => (
                    <tr key={s.file}>
                      <td className="py-1.5 pr-3 font-mono">{s.file}</td>
                      <td className="py-1.5 pr-3 text-zinc-600 dark:text-zinc-400">{s.area}</td>
                      <td className="py-1.5 pr-3">{s.author === "Trent" ? <Badge tone="blue">you</Badge> : s.author}</td>
                      <td className="py-1.5 pr-3 text-right tabular-nums">{s.tests ?? "—"}</td>
                      <td className="py-1.5">
                        <Badge tone={SUITE_TONE[s.state]}>{s.state}</Badge>
                        {s.note && <span className="ml-1.5 text-zinc-500">{s.note}</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-2 text-[11px] text-zinc-500">
                Counts are test functions on main; parametrised cases count once. Growth-goal coverage gets rows once the team picks its goals.
              </p>
            </div>
            <div className="flex flex-col gap-2">
              <p className="text-xs font-medium text-zinc-700 dark:text-zinc-300">CI jobs (.github/workflows/ci.yml)</p>
              {CI_JOBS.map((j) => (
                <div key={j.name} className="rounded-md border border-zinc-200 p-2.5 text-xs dark:border-zinc-800">
                  <p className="font-mono font-semibold text-zinc-900 dark:text-zinc-100">{j.name}</p>
                  <p className="mt-0.5 text-zinc-600 dark:text-zinc-400">{j.does}</p>
                  <p className="mt-1 text-amber-800 dark:text-amber-300">Gap: {j.gap}</p>
                </div>
              ))}
            </div>
          </div>
        </Panel>
      </section>

      {/* 4 + 7. Deploy and freeze prep */}
      <section id="deploy" className="scroll-mt-4">
        <Panel title="4 · Deploy (and 7 · freeze prep)" subtitle={`${doneCount} of ${checklist.length} checklist items done · ticks are local to this page`}>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {ENVS.map((e) => (
              <div
                key={e.name}
                className={`flex flex-col gap-1 rounded-md border p-3 text-xs ${
                  e.state === "undecided" ? "border-amber-300 bg-amber-50 dark:border-amber-900 dark:bg-amber-950/30" : "border-zinc-200 dark:border-zinc-800"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{e.name}</p>
                  <Badge tone={ENV_TONE[e.state]}>{e.state}</Badge>
                </div>
                <p className="font-mono text-zinc-500">{e.where}</p>
                <p className="text-zinc-600 dark:text-zinc-400">{e.detail}</p>
              </div>
            ))}
          </div>
          <div className="mt-3 grid items-center gap-2 text-xs sm:grid-cols-[auto_1fr_auto_1fr_auto_1fr_auto] sm:gap-1" aria-label="Request path in production">
            {["Vercel frontend", "Cloud Run API", "Production MySQL"].map((n, i) => (
              <div key={n} className="contents">
                {i > 0 && (
                  <span aria-hidden className="hidden text-center text-zinc-400 sm:block">
                    →
                  </span>
                )}
                <span
                  className={`rounded-md border px-2 py-1.5 text-center ${
                    i === 2 ? "border-dashed border-amber-400 text-amber-800 dark:text-amber-300" : "border-zinc-300 text-zinc-700 dark:border-zinc-700 dark:text-zinc-300"
                  }`}
                >
                  {n}
                  {i === 2 && " · ?"}
                </span>
              </div>
            ))}
          </div>
          <ul className="mt-4 grid gap-x-6 gap-y-1.5 text-xs md:grid-cols-2">
            {DEPLOY_CHECKLIST.map((c, i) => (
              <li key={c.text}>
                <label className="flex items-start gap-2">
                  <input
                    type="checkbox"
                    checked={checklist[i]}
                    onChange={() => setChecklist((list) => list.map((v, j) => (j === i ? !v : v)))}
                    className="mt-0.5 accent-blue-600"
                  />
                  <span className={checklist[i] ? "text-zinc-400 line-through" : "text-zinc-700 dark:text-zinc-300"}>
                    <span className="mr-1 font-mono text-[10px] text-zinc-500">S{c.sprint}</span>
                    {c.text}
                  </span>
                </label>
              </li>
            ))}
          </ul>
        </Panel>
      </section>

      {/* 5. Events → metrics */}
      <section id="events" className="scroll-mt-4">
        <Panel title="5 · Events → metrics" subtitle={`${rejected.length} event types main already writes would be rejected by feature/simulation's allowlist`}>
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[28rem] text-left text-xs">
                <thead className="text-zinc-500">
                  <tr className="border-b border-zinc-200 dark:border-zinc-800">
                    <th className="py-1.5 pr-3 font-medium">event type</th>
                    <th className="py-1.5 pr-3 font-medium">Written by</th>
                    <th className="py-1.5 pr-3 font-medium">On main</th>
                    <th className="py-1.5 font-medium">Branch allowlist</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-100 dark:divide-zinc-900">
                  {EVENT_TYPES.map((e) => (
                    <tr key={e.type} className={e.onMain && !e.inAllowlist ? "bg-red-50/60 dark:bg-red-950/20" : undefined}>
                      <td className="py-1.5 pr-3 font-mono">{e.type}</td>
                      <td className="py-1.5 pr-3">{e.writer.startsWith("Trent") ? <Badge tone="blue">you · workforce</Badge> : e.writer}</td>
                      <td className="py-1.5 pr-3">{e.onMain ? "yes" : <span className="text-zinc-500">branch only</span>}</td>
                      <td className="py-1.5">
                        {e.inAllowlist ? (
                          <span className="text-emerald-700 dark:text-emerald-400">✓ allowed</span>
                        ) : (
                          <span className="font-medium text-red-700 dark:text-red-400">✗ ValueError</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="flex flex-col gap-2 text-xs">
              <p className="font-medium text-zinc-700 dark:text-zinc-300">The events table itself doesn&apos;t match</p>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[26rem] text-left">
                  <thead className="text-zinc-500">
                    <tr className="border-b border-zinc-200 dark:border-zinc-800">
                      <th className="py-1.5 pr-3 font-medium">main (migration 0002)</th>
                      <th className="py-1.5 font-medium">feature/simulation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-zinc-100 font-mono dark:divide-zinc-900">
                    {EVENT_COLUMNS.map((c) => (
                      <tr key={c.main}>
                        <td className="py-1.5 pr-3">{c.main}</td>
                        <td className={`py-1.5 ${c.clash ? "font-semibold text-red-700 dark:text-red-400" : "text-zinc-500"}`}>{c.branch}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <ul className="list-disc space-y-0.5 pl-4 text-zinc-600 dark:text-zinc-400">
                <li>Main&apos;s table is the one that&apos;s migrated, and its triggers make it append-only, so the branch should adopt main&apos;s names.</li>
                <li>The frontend throughput chart already calls GET /api/v1/metrics/throughput, which only exists on the branch (404 on main).</li>
                <li>Your side: an integration test that writes each worker_* event through the API and reads it back through the metrics endpoint.</li>
              </ul>
            </div>
          </div>
        </Panel>
      </section>

      {/* 6. Decisions */}
      <section id="decisions" className="scroll-mt-4">
        <Panel
          title="6 · Decisions"
          subtitle={`${Object.keys(decided).length} of ${DECISIONS.length} settled · choices here are local to this page`}
          actions={
            <Link href="/concepts/workforce" className="text-xs text-blue-700 underline dark:text-blue-400">
              See the grid bound on the workforce concept →
            </Link>
          }
        >
          <ul className="grid gap-3 lg:grid-cols-2">
            {DECISIONS.map((d) => {
              const pick = decided[d.id];
              return (
                <li key={d.id} className={`rounded-md border p-3 text-xs ${pick ? "border-emerald-300 dark:border-emerald-900" : "border-zinc-200 dark:border-zinc-800"}`}>
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100">{d.question}</p>
                    {pick ? <Badge tone="emerald">settled</Badge> : <Badge tone="amber">{d.who}</Badge>}
                  </div>
                  <fieldset className="mt-2 flex flex-col gap-1">
                    <legend className="sr-only">{d.question}</legend>
                    {d.options.map((o) => (
                      <label key={o} className="flex items-start gap-2 text-zinc-700 dark:text-zinc-300">
                        <input type="radio" name={d.id} checked={pick === o} onChange={() => setDecided((m) => ({ ...m, [d.id]: o }))} className="mt-0.5 accent-blue-600" />
                        {o}
                      </label>
                    ))}
                  </fieldset>
                  <p className="mt-2 text-zinc-600 dark:text-zinc-400">
                    <span className="font-semibold">Leaning:</span> {d.lean}
                  </p>
                  <p className="text-zinc-500">Blocks: {d.blocks}</p>
                </li>
              );
            })}
          </ul>
        </Panel>
      </section>
    </div>
  );
}

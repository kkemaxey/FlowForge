import Link from "next/link";

import { Badge, ConceptBanner } from "@/components/concepts/ConceptKit";
import { PageHeader } from "@/components/portal/Wireframe";

// Index of the future-state concepts. Each card says what exists today, what the concept adds and which
// sprint goal it serves, so the team can pick pieces rather than adopt a whole page.

const CONCEPTS = [
  {
    href: "/concepts/console",
    title: "Operations console v2",
    who: "Supervisor",
    target: "Growth",
    today: "/console stacks the grid, live board, workforce and controls in two columns; the exception feed is a placeholder.",
    adds: [
      "Always-on run bar (sim run, clock, speed, data freshness)",
      "KPI tiles with targets and sparklines",
      "SVG floor map with worker markers, travel paths and a congestion layer",
      "Exception queue with the auto-reassignment trail and one-click fixes",
      "SLA watchlist with expedite and undo",
    ],
  },
  {
    href: "/concepts/simulation",
    title: "Simulation control room",
    who: "Admin",
    target: "MVP → Growth",
    today: "/admin/simulation is four dashed boxes.",
    adds: [
      "Start, pause, stop and a typed-confirm reset",
      "Order rate, seed and assigner, validated like the API",
      "Scenario presets for demos and drills",
      "Exception injector with a log",
      "Run history with a fair, same-seed comparison",
    ],
  },
  {
    href: "/concepts/layout-editor",
    title: "Layout editor",
    who: "Admin",
    target: "Growth",
    today: "/admin/layout is four dashed boxes; the floor is seeded in code.",
    adds: ["Paint cells by click or drag, keys 1–4 for the brush", "Live reachability and stock checks that block publishing", "Draft, undo, versions and JSON import/export"],
  },
  {
    href: "/concepts/system",
    title: "System health",
    who: "Admin",
    target: "Stretch",
    today: "Only GET /health, plus request-id lines in the server log.",
    adds: ["One health verdict with what to try", "Service tiles for API, DB, assigner, simulator, generator, auth", "Searchable request log keyed by request id", "Route catalogue: live, on a branch or planned"],
  },
];

const PRINCIPLES = [
  ["Decide, then act, in one place", "Every problem shown on the console carries the action that fixes it, so nobody has to go hunting."],
  ["Never colour alone", "Every status has a word, shape or pattern as well (round humans, square robots, struck-through when down, hatched blocked cells)."],
  ["Stale beats blank", "Keep the last good data on a failed poll and say how old it is."],
  ["Undo over confirm", "Routine actions (expedite, acknowledge) happen at once with an undo; only destructive ones (reset) ask first."],
  ["Same palette as today", "Blue primary, orange WIP, emerald on-time, red exceptions, zinc neutrals, so a concept can be lifted into the real page without a restyle."],
] as const;

export default function ConceptsIndexPage() {
  return (
    <div className="flex flex-col gap-4">
      <ConceptBanner target="Sprints 3–4 and stretch" buildsOn="the current portal wireframes">
        Higher-fidelity wireframes of where the console could go next. Everything is clickable and runs on mock data.
      </ConceptBanner>
      <PageHeader title="Console concepts" subtitle="Future directions for the supervisor console and the admin back office" />

      <div className="grid gap-4 lg:grid-cols-2">
        {CONCEPTS.map((c) => (
          <Link
            key={c.href}
            href={c.href}
            className="group flex flex-col gap-3 rounded-lg border border-zinc-200 bg-white p-4 hover:border-blue-400 dark:border-zinc-800 dark:bg-zinc-950 dark:hover:border-blue-700"
          >
            <div className="flex items-start justify-between gap-2">
              <h2 className="font-semibold text-zinc-900 group-hover:text-blue-700 dark:text-zinc-100 dark:group-hover:text-blue-400">{c.title} →</h2>
              <div className="flex shrink-0 gap-1">
                <Badge tone={c.who === "Admin" ? "orange" : "violet"}>{c.who}</Badge>
                <Badge tone="blue">{c.target}</Badge>
              </div>
            </div>
            <p className="text-xs text-zinc-500">
              <span className="font-medium text-zinc-600 dark:text-zinc-400">Today:</span> {c.today}
            </p>
            <ul className="list-disc space-y-0.5 pl-5 text-sm text-zinc-700 dark:text-zinc-300">
              {c.adds.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </Link>
        ))}
      </div>

      <section className="rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="mb-3 text-sm font-semibold text-zinc-700 dark:text-zinc-300">Design principles across the concepts</h2>
        <dl className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-3">
          {PRINCIPLES.map(([title, body]) => (
            <div key={title}>
              <dt className="font-medium text-zinc-900 dark:text-zinc-100">{title}</dt>
              <dd className="mt-0.5 text-zinc-600 dark:text-zinc-400">{body}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="rounded-lg border border-zinc-200 bg-white p-4 text-sm dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="mb-2 text-sm font-semibold text-zinc-700 dark:text-zinc-300">What the backend would need</h2>
        <ul className="list-disc space-y-1 pl-5 text-zinc-600 dark:text-zinc-400">
          <li>
            <span className="font-mono text-xs">GET /api/v1/orders</span> with due_at, for the SLA watchlist (today the board fetches orders one by one).
          </li>
          <li>Per-cell dwell time in the events module, for the congestion layer.</li>
          <li>
            <span className="font-mono text-xs">sim_runs</span> results joined with events, for run history and comparison.
          </li>
          <li>
            A versioned <span className="font-mono text-xs">PUT /api/v1/warehouse/layout</span>, for the layout editor.
          </li>
          <li>
            <span className="font-mono text-xs">GET /api/v1/system/health</span>, plus keeping recent request-log lines somewhere queryable, for System health.
          </li>
        </ul>
      </section>
    </div>
  );
}

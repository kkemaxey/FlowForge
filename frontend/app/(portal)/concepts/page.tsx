import Link from "next/link";

import { Badge, ConceptBanner } from "@/components/concepts/ConceptKit";
import { PageHeader } from "@/components/portal/Wireframe";
import { OPEN_STEPS } from "@/mocks/conceptMocks";

// Index of the concepts in Trent's areas. Everything outside workforce, deploy, CI and tests was trimmed.

const CONCEPTS = [
  {
    href: "/concepts/backend",
    title: "Backend console",
    today: "Open work is spread across the sprint plan, the walkthrough's open questions and CI logs.",
    adds: ["The seven open steps with what each waits on", "Route gates: required vs enforced on main", "Tests and CI coverage by suite", "Deploy environments and checklist", "Events → metrics mismatches with feature/simulation", "Decisions to settle, with a leaning"],
  },
  {
    href: "/concepts/workforce",
    title: "Workforce",
    today: "The console panel lists, adds, edits and deactivates workers; /admin/workforce is a placeholder.",
    adds: ["A “call as” switch previewing the auth gates", "Position picker with the proposed grid bound", "Version-conflict, worker_busy and open-assignment cases on demand", "Request and response for every action", "Per-worker history from the events log"],
  },
];

export default function ConceptsIndexPage() {
  const ready = OPEN_STEPS.filter((s) => s.state === "ready").length;
  return (
    <div className="flex flex-col gap-4">
      <ConceptBanner target="Sprints 3–5" buildsOn="Trent's areas: workforce, Dockerfile, CI, tests">
        Clickable wireframes for the parts of FlowForge Trent owns. Mock data only.
      </ConceptBanner>
      <PageHeader title="Concepts" subtitle={`${OPEN_STEPS.length} open steps, ${ready} ready to start`} />

      <div className="grid gap-4 lg:grid-cols-2">
        {CONCEPTS.map((c) => (
          <Link
            key={c.href}
            href={c.href}
            className="group flex flex-col gap-3 rounded-lg border border-zinc-200 bg-white p-4 hover:border-blue-400 dark:border-zinc-800 dark:bg-zinc-950 dark:hover:border-blue-700"
          >
            <div className="flex items-start justify-between gap-2">
              <h2 className="font-semibold text-zinc-900 group-hover:text-blue-700 dark:text-zinc-100 dark:group-hover:text-blue-400">{c.title} →</h2>
              <Badge tone="orange">Admin</Badge>
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

      <section className="rounded-lg border border-zinc-200 bg-white p-4 text-sm dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="mb-2 text-sm font-semibold text-zinc-700 dark:text-zinc-300">Backend changes these concepts assume</h2>
        <ul className="list-disc space-y-1 pl-5 text-zinc-600 dark:text-zinc-400">
          <li>
            <span className="font-mono text-xs">current_app_user</span> on the workforce router and <span className="font-mono text-xs">require_supervisor</span> on its writes.
          </li>
          <li>
            <span className="font-mono text-xs">WAREHOUSE_WIDTH</span> / <span className="font-mono text-xs">WAREHOUSE_HEIGHT</span> and a 422 <span className="font-mono text-xs">position_off_grid</span>.
          </li>
          <li>
            <span className="font-mono text-xs">GET /api/v1/workers/{"{id}"}/events</span>, read-only over the events table.
          </li>
          <li>feature/simulation adopting main&apos;s events columns and allowlisting every type main writes.</li>
        </ul>
      </section>
    </div>
  );
}

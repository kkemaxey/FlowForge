import { ConceptBanner } from "@/components/concepts/ConceptKit";
import { Annotation, PageHeader } from "@/components/portal/Wireframe";

import { ConsoleV2 } from "./ConsoleV2";

export default function ConsoleConceptPage() {
  return (
    <div className="flex flex-col gap-4">
      <ConceptBanner target="Sprint 3–4 (growth: SLA, bottlenecks)" buildsOn="LiveBoard, KpiStrip, WarehouseGrid, Controls" />
      <PageHeader title="Operations console v2" subtitle="A single screen to run a shift from: see it, decide, act" />
      <ConsoleV2 />
      <Annotation
        notes={{
          rules: [
            "Run bar is always visible: sim run, clock, speed, assigner and data freshness. A stale poll turns the dot red and keeps the last good data.",
            "KPI tiles keep the live board's colours and add a target and a 30-minute sparkline; the number is always in text.",
            "Map layers are toggles. Congestion comes from worker dwell time per walkable cell (growth goal: bottleneck highlighting).",
            "Exceptions sort open first, then auto-fixing, then resolved. Each shows its auto-reassignment trail and one suggested fix.",
            "SLA watchlist: late orders first, then at risk (projected finish after due_at). Expedite is one click with an undo toast.",
            "Every action posts to an existing endpoint: reassign → POST /tasks/{id}/reassign, expedite → POST /orders/{id}/expedite.",
          ],
          supervisor: "Everything on this page. Sim speed is display only.",
          admin: "Same, plus the link through to Simulation controls.",
        }}
      />
    </div>
  );
}

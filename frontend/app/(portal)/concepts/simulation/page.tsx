import { ConceptBanner } from "@/components/concepts/ConceptKit";
import { Annotation, PageHeader } from "@/components/portal/Wireframe";
import { DEMO_WAREHOUSE as warehouse } from "@/mocks/demoWarehouse";

import { SimControlRoom } from "./SimControlRoom";

export default function SimulationConceptPage() {
  return (
    <div className="flex flex-col gap-4">
      <ConceptBanner target="Sprint 3 (admin), run comparison in Sprint 4" buildsOn="generator and assignment APIs, /admin/simulation" />
      <PageHeader title="Simulation control room" subtitle={`${warehouse.name} · admin only`} />
      <SimControlRoom />
      <Annotation
        notes={{
          rules: [
            "Start sends POST /generator/start with order_rate and seed; the API already validates 0 < rate ≤ 600 and the seed range, and the form mirrors that.",
            "Each start creates a sim_runs row with its algorithm and seed, so the history table and comparison come from sim_runs plus events.",
            "Reset needs the word typed in: it clears orders, tasks and assignments for this warehouse, restores stock and keeps run history.",
            "Injected exceptions go through the same exception flow as simulated ones, tagged source = admin so metrics can leave them out.",
            "A comparison is labelled fair only when both runs used the same seed and order rate.",
          ],
          supervisor: "No access (redirected to /403). Sees the sim clock on the console.",
          admin: "Starts, pauses, resets, picks scenarios, injects exceptions and compares runs.",
        }}
      />
    </div>
  );
}

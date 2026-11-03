import { ConceptBanner } from "@/components/concepts/ConceptKit";
import { Annotation, PageHeader } from "@/components/portal/Wireframe";
import { DEMO_WAREHOUSE as warehouse } from "@/mocks/demoWarehouse";

import { LayoutEditor } from "./LayoutEditor";

export default function LayoutEditorConceptPage() {
  return (
    <div className="flex flex-col gap-4">
      <ConceptBanner target="Sprint 4 (growth)" buildsOn="WarehouseGrid, demo warehouse, /admin/layout" />
      <PageHeader title="Layout editor" subtitle={`${warehouse.name} · admin only · try painting`} />
      <LayoutEditor />
      <Annotation
        notes={{
          rules: [
            "Edits are a draft until published. Publishing writes one new layout version; running sims keep the old one until reset.",
            "Blocking checks: at least one station, every storage cell reachable on foot from a station, and no stocked bin changed to another type.",
            "Warnings don't block: cut-off aisle cells, new storage cells that need codes.",
            "Hovering a check outlines the cells it's about; the cell panel shows the code, stock and what it was before.",
            "Resize stays disabled while any location would fall outside the new size.",
          ],
          supervisor: "No access (redirected to /403).",
          admin: "Paints cells, imports and exports JSON, publishes versions.",
        }}
      />
    </div>
  );
}

import { Card } from "@/components/ui/Card";
import { WarehouseGrid } from "@/components/grid/WarehouseGrid";
import { Annotation, PageHeader, PlaceholderBox } from "@/components/portal/Wireframe";
import { Controls } from "@/app/console/controls/Controls";
import { LiveBoard } from "@/app/console/live-board/LiveBoard";
import { WorkforcePanel } from "@/app/console/workforce/WorkforcePanel";
import { DEMO_WAREHOUSE as warehouse } from "@/mocks/demoWarehouse";

// Operations console. The live board is built; the worker panel (Trent) and the reassign and expedite
// controls (Aalan) render their own components, and the exception feed is still a placeholder.
export default function ConsolePage() {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <PageHeader title="Operations console" subtitle={warehouse.name} />
        {/* Display only: admins change the speed on the Simulation page. */}
        <p className="rounded-md border border-blue-200 bg-blue-50 px-2 py-1 text-xs text-blue-800 dark:border-blue-900 dark:bg-blue-950 dark:text-blue-300">
          Sim clock <span className="font-semibold tabular-nums">1×</span> (1× / 10× / 60×)
        </p>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <div className="flex min-w-0 flex-col gap-4">
          <Card title="Grid map">
            <WarehouseGrid warehouse={warehouse} />
            <p className="mt-2 text-xs text-zinc-500">Worker and task markers on the map: Aalan (console/grid-map).</p>
          </Card>
          <div className="grid gap-4 sm:grid-cols-2">
            <WorkforcePanel />
            <Controls />
          </div>
        </div>
        <div className="flex min-w-0 flex-col gap-4">
          <LiveBoard />
          <PlaceholderBox label="Exception feed">Newest first, with acknowledge and the auto-reassignment trail.</PlaceholderBox>
        </div>
      </div>
      <Annotation
        notes={{
          rules: [
            "Live board polls every 2 s and keeps the last good data if a poll fails.",
            "On-time % = completed orders finished by due_at ÷ completed orders; a dash until one completes.",
            "Late orders are flagged with a red row and the word “late”, not color alone.",
          ],
          supervisor: "Views everything here; reassigns tasks, expedites orders, acknowledges exceptions.",
          admin: "Same as supervisor. Sim speed and exception injection live on the Simulation page.",
        }}
      />
    </div>
  );
}

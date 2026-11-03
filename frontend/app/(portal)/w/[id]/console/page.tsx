import { Card } from "@/components/ui/Card";
import { WarehouseGrid } from "@/components/grid/WarehouseGrid";
import { Annotation, PageHeader, PlaceholderBox } from "@/components/portal/Wireframe";
import { LiveBoard } from "@/app/console/live-board/LiveBoard";
import { warehouseOr404 } from "@/mocks/warehouses";

// Operations console for one warehouse. The live board (orders by status, KPI strip, task counts) is
// built; the panels owned by other teammates are dashed placeholders.
export default async function ConsolePage({ params }: PageProps<"/w/[id]/console">) {
  const warehouse = warehouseOr404((await params).id);

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
            <PlaceholderBox label="Worker panel">Name, kind, status, current task per worker.</PlaceholderBox>
            <PlaceholderBox label="Reassign and expedite">Move a task to another worker; bump an order&apos;s priority.</PlaceholderBox>
          </div>
        </div>
        <div className="flex min-w-0 flex-col gap-4">
          <LiveBoard warehouseId={warehouse.id} />
          <PlaceholderBox label="Exception feed">Newest first, with acknowledge and the auto-reassignment trail.</PlaceholderBox>
        </div>
      </div>
      <Annotation
        notes={{
          rules: [
            "Everything on this page is scoped to this warehouse (?warehouse_id=).",
            "The assigner only matches workers and tasks in the same warehouse.",
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

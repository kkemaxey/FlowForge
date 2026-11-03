import { Annotation, PageHeader, PlaceholderBox } from "@/components/portal/Wireframe";
import { ConsoleDataProvider } from "@/app/console/ConsoleData";
import { Controls } from "@/app/console/controls/Controls";
import { LiveGridMap } from "@/app/console/grid-map/LiveGridMap";
import { LiveBoard } from "@/app/console/live-board/LiveBoard";
import { WorkforcePanel } from "@/app/console/workforce/WorkforcePanel";
import { DEMO_WAREHOUSE as warehouse } from "@/mocks/demoWarehouse";

// Operations console: the grid map and controls (Aalan), the live board (Jayden) and the worker panel
// (Trent). The exception feed is still a placeholder.
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
        <ConsoleDataProvider>
          <div className="flex min-w-0 flex-col gap-4">
            <LiveGridMap />
            <div className="grid gap-4 sm:grid-cols-2">
              <WorkforcePanel />
              <Controls />
            </div>
          </div>
        </ConsoleDataProvider>
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

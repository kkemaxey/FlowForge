import { Annotation, PageHeader, PlaceholderBox } from "@/components/portal/Wireframe";
import { ThroughputChart } from "@/app/console/live-board/ThroughputChart";
import { warehouseOr404 } from "@/mocks/warehouses";

export default async function MetricsPage({ params }: PageProps<"/w/[id]/metrics">) {
  const warehouse = warehouseOr404((await params).id);

  return (
    <div className="flex flex-col gap-4">
      <PageHeader title="Metrics" subtitle={warehouse.name} />
      <ThroughputChart warehouseId={warehouse.id} />
      <PlaceholderBox label="Assigner comparison by sim run (later)">
        <div className="overflow-x-auto">
          <table className="mt-1 w-full min-w-md text-left text-xs">
            <thead>
              <tr className="border-b border-zinc-300 dark:border-zinc-700">
                <th className="py-1 pr-3 font-medium">Sim run</th>
                <th className="py-1 pr-3 font-medium">Algorithm</th>
                <th className="py-1 pr-3 text-right font-medium">Units/hr</th>
                <th className="py-1 pr-3 text-right font-medium">On-time %</th>
                <th className="py-1 text-right font-medium">Avg travel (m)</th>
              </tr>
            </thead>
            <tbody>
              {["greedy", "custom"].map((algorithm) => (
                <tr key={algorithm}>
                  <td className="py-1 pr-3">—</td>
                  <td className="py-1 pr-3">{algorithm}</td>
                  <td className="py-1 pr-3 text-right">—</td>
                  <td className="py-1 pr-3 text-right">—</td>
                  <td className="py-1 text-right">—</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </PlaceholderBox>
      <Annotation
        notes={{
          rules: [
            "Throughput is units completed per minute over the last 30 minutes, from GET /events/metrics/throughput.",
            "The current minute is still filling, so it is drawn hollow.",
            "The summary line and data table carry the same numbers as the chart.",
            "Assigner comparison groups metrics by sim_runs.algorithm once the custom assigner exists.",
          ],
          supervisor: "Views all metrics.",
          admin: "Views all metrics; starts the sim runs being compared (Simulation page).",
        }}
      />
    </div>
  );
}

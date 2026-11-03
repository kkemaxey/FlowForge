import type { LiveMetrics, Order, Task } from "./data";
import { onTimeRate, workInProgress } from "./boardLogic";

// The three headline numbers across the top of the console: throughput, WIP and on-time %.
// Pure display: throughput comes from the metrics endpoint (a dash while it's missing); WIP and on-time are
// worked out from orders and tasks in boardLogic.ts.

export function KpiStrip({ metrics, orders, tasks }: { metrics: LiveMetrics | null; orders: Order[]; tasks: Task[] }) {
  const onTime = onTimeRate(orders);
  const wip = workInProgress(orders, tasks);

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <Tile
        label="Throughput"
        value={metrics ? metrics.units_per_hour.toLocaleString() : "—"}
        unit={metrics ? "units/hr" : undefined}
        accent="border-l-blue-600"
        detail={metrics ? `${metrics.tasks_per_hour.toLocaleString()} tasks/hr · last 5 min` : "Waiting on the metrics endpoint"}
      />
      <Tile
        label="WIP"
        value={wip.total.toLocaleString()}
        accent="border-l-orange-500"
        detail={`${wip.ordersInProgress} orders in progress · ${wip.tasksAssigned} tasks assigned`}
      />
      <Tile
        label="On-time"
        value={onTime === null ? "—" : String(onTime)}
        unit={onTime === null ? undefined : "%"}
        accent="border-l-emerald-500"
        detail="Completed orders that finished by their due time"
      />
    </div>
  );
}

// A single metric box, with a colored left edge so the three read apart at a glance.
function Tile({
  label,
  value,
  unit,
  detail,
  accent,
}: {
  label: string;
  value: string;
  unit?: string;
  detail: string;
  accent: string;
}) {
  return (
    <div className={`rounded-md border border-l-4 border-zinc-200 p-3 dark:border-zinc-800 ${accent}`}>
      <p className="text-xs font-medium text-zinc-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-100">
        {value}
        {unit && <span className="ml-1 text-sm font-normal text-zinc-500">{unit}</span>}
      </p>
      <p className="mt-0.5 text-xs text-zinc-500">{detail}</p>
    </div>
  );
}

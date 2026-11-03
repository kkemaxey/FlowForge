import type { LiveMetrics, Order } from "./data";
import { onTimeRate, wipTotal } from "./boardLogic";

// The three headline numbers across the top of the console: throughput, WIP and on-time %.
// Pure display: the numbers come from the metrics endpoint and boardLogic.ts.

export function KpiStrip({ metrics, orders }: { metrics: LiveMetrics; orders: Order[] }) {
  const onTime = onTimeRate(orders);

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <Tile
        label="Throughput"
        value={metrics.units_per_hour.toLocaleString()}
        unit="units/hr"
        accent="border-l-blue-600"
        detail={`${metrics.tasks_per_hour.toLocaleString()} tasks/hr · last 5 min`}
      />
      <Tile
        label="WIP"
        value={wipTotal(metrics).toLocaleString()}
        accent="border-l-orange-500"
        detail={`${metrics.orders_in_progress} orders in progress · ${metrics.tasks_assigned} tasks assigned`}
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

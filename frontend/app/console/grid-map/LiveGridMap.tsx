"use client";

import { Card } from "@/components/ui/Card";
import { DEMO_WAREHOUSE } from "@/mocks/demoWarehouse";

import { useConsoleData } from "../ConsoleData";
import { GridMap } from "./GridMap";

/** The grid map, fed by the console's live data. */
export function LiveGridMap() {
  const { locations, workers, tasks, loading, error } = useConsoleData();

  if (loading) return <Card title="Grid map">Loading the warehouse…</Card>;
  return (
    <div className="flex min-w-0 flex-col gap-2">
      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
      <GridMap
        locations={locations}
        workers={workers.filter((w) => w.is_active)}
        tasks={tasks}
        minWidth={DEMO_WAREHOUSE.width}
        minHeight={DEMO_WAREHOUSE.height}
      />
    </div>
  );
}

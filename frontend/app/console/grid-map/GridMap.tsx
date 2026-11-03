import { Card } from "@/components/ui/Card";

import type { GridLocation, GridTask, GridWorker, LocationKind, WorkerStatus } from "../types";

const KIND_SYMBOL: Record<LocationKind, string> = { storage: "S", pick_station: "P", dock: "D", charger: "C" };

const KIND_CLASS: Record<LocationKind, string> = {
  storage: "bg-blue-50 dark:bg-blue-950",
  pick_station: "bg-green-100 dark:bg-green-950",
  dock: "bg-purple-100 dark:bg-purple-950",
  charger: "bg-orange-100 dark:bg-orange-950",
};

const STATUS_CLASS: Record<WorkerStatus, string> = {
  idle: "bg-emerald-600 text-white",
  busy: "bg-amber-500 text-black",
  down: "bg-zinc-500 text-white line-through",
};

const STATUS_SYMBOL: Record<WorkerStatus, string> = { idle: "i", busy: "b", down: "x" };

function key(x: number, y: number) {
  return `${x},${y}`;
}

function group<T>(items: T[], at: (item: T) => string) {
  const map = new Map<string, T[]>();
  for (const item of items) {
    const k = at(item);
    map.set(k, [...(map.get(k) ?? []), item]);
  }
  return map;
}

export interface GridMapProps {
  locations: GridLocation[];
  workers: GridWorker[];
  tasks: GridTask[];
}

export function GridMap({ locations, workers, tasks }: GridMapProps) {
  // Size comes from the data: the largest coordinate plus 1.
  const all = [...locations, ...workers, ...tasks.map((t) => t.location)];
  const width = all.reduce((m, p) => Math.max(m, p.x + 1), 0);
  const height = all.reduce((m, p) => Math.max(m, p.y + 1), 0);

  const locationAt = new Map(locations.map((l) => [key(l.x, l.y), l]));
  const workersAt = group(workers, (w) => key(w.x, w.y));
  const tasksAt = group(tasks, (t) => key(t.location.x, t.location.y));
  const workerById = new Map(workers.map((w) => [w.id, w]));

  if (width === 0) {
    return <Card title="Grid map">No locations yet.</Card>;
  }

  return (
    <Card title="Grid map">
      <div className="overflow-x-auto">
        <table className="border-collapse text-center text-[11px]">
          <thead>
            <tr>
              <th className="p-1 text-zinc-500" scope="col">
                <span className="sr-only">Y \ X</span>
              </th>
              {Array.from({ length: width }, (_, x) => (
                <th key={x} scope="col" className="p-1 font-medium text-zinc-500">
                  {x}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: height }, (_, y) => (
              <tr key={y}>
                <th scope="row" className="p-1 pr-2 font-medium text-zinc-500">
                  {y}
                </th>
                {Array.from({ length: width }, (_, x) => {
                  const k = key(x, y);
                  const location = locationAt.get(k);
                  const cellWorkers = workersAt.get(k) ?? [];
                  const cellTasks = tasksAt.get(k) ?? [];
                  const label = [
                    `(${x}, ${y})`,
                    location ? `${location.kind.replace("_", " ")}${location.aisle ? ` ${location.aisle}` : ""}` : "walkway",
                    ...cellWorkers.map((w) => `${w.kind} ${w.name} ${w.status}`),
                    ...cellTasks.map(
                      (t) =>
                        `task ${t.task_id} ${t.status}${t.current_assignment ? ` worker ${t.current_assignment.worker_id}` : ""}`,
                    ),
                  ].join(", ");
                  return (
                    <td
                      key={x}
                      title={label}
                      aria-label={label}
                      className={`relative h-12 w-12 border border-zinc-200 align-middle dark:border-zinc-800 ${
                        location ? KIND_CLASS[location.kind] : "bg-white dark:bg-zinc-950"
                      }`}
                    >
                      {location && (
                        <span className="absolute left-0.5 top-0 text-[9px] text-zinc-400" aria-hidden>
                          {KIND_SYMBOL[location.kind]}
                        </span>
                      )}
                      {cellTasks.map((t) => {
                        const holder = t.current_assignment && workerById.get(t.current_assignment.worker_id);
                        const exception = t.status === "exception";
                        return (
                          <span
                            key={t.task_id}
                            className={`absolute right-0.5 top-0 rounded-sm px-0.5 text-[9px] font-bold ${
                              exception
                                ? "bg-red-600 text-white ring-2 ring-red-300 dark:ring-red-800"
                                : "border border-sky-600 text-sky-700 dark:text-sky-300"
                            }`}
                          >
                            {exception ? "!" : "T"}
                            {t.task_id}
                            {t.current_assignment && `→${holder?.name ?? `#${t.current_assignment.worker_id}`}`}
                          </span>
                        );
                      })}
                      <span className="flex flex-wrap justify-center gap-0.5">
                        {cellWorkers.map((w) => (
                          <span
                            key={w.id}
                            className={`inline-flex h-5 min-w-5 items-center justify-center px-0.5 text-[10px] font-bold ${
                              w.kind === "robot" ? "rounded-sm" : "rounded-full"
                            } ${STATUS_CLASS[w.status]}`}
                          >
                            {w.kind === "robot" ? "R" : "H"}
                            {STATUS_SYMBOL[w.status]}
                          </span>
                        ))}
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-600 dark:text-zinc-400">
        <li>H round = human, R square = robot</li>
        <li>i idle (green), b busy (amber), x down (grey)</li>
        <li>S storage, P pick station</li>
        <li>T# assigned task → worker</li>
        <li>
          <span className="font-bold text-red-600">!#</span> exception task
        </li>
      </ul>
    </Card>
  );
}

import type { GridLocation, GridTask, GridWorker } from "@/app/console/types";

import { buildDemoWarehouse, DEMO_WORKERS } from "./demoWarehouse";

// Mocks for the grid map and controls, shaped like GET /locations, /workers and /tasks.

const warehouse = buildDemoWarehouse(1);

export const MOCK_LOCATIONS: GridLocation[] = [
  ...warehouse.locations.map((l, i) => ({
    location_id: i + 1,
    x: l.x,
    y: l.y,
    kind: "storage" as const,
    zone: l.code[0],
    aisle: l.code.slice(0, 2),
  })),
  { location_id: 100, x: 3, y: 0, kind: "pick_station", zone: null, aisle: null },
  { location_id: 101, x: 6, y: 0, kind: "pick_station", zone: null, aisle: null },
];

export const MOCK_WORKERS: GridWorker[] = DEMO_WORKERS.map((w) => ({
  ...w,
  status: w.id === 1 || w.id === 6 ? "busy" : w.id === 5 ? "down" : "idle",
  is_active: true,
}));

const loc = (id: number) => {
  const l = MOCK_LOCATIONS[id - 1];
  return { location_id: l.location_id, x: l.x, y: l.y, zone: l.zone, aisle: l.aisle };
};

export const MOCK_TASKS: GridTask[] = [
  { task_id: 1, order_id: 1, status: "assigned", priority: 0, version: 2, location: loc(5), current_assignment: { assignment_id: 1, worker_id: 1 } },
  { task_id: 2, order_id: 1, status: "assigned", priority: 0, version: 2, location: loc(20), current_assignment: { assignment_id: 2, worker_id: 6 } },
  { task_id: 3, order_id: 2, status: "open", priority: 0, version: 1, location: loc(30), current_assignment: null },
  { task_id: 4, order_id: 2, status: "exception", priority: 0, version: 3, location: loc(40), current_assignment: null },
];

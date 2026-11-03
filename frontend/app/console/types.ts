// Shapes of the backend rows the grid map and controls use (snake_case, as the API returns them).
// Workers use the shared Worker type from @/types.

export type LocationKind = "storage" | "pick_station" | "dock" | "charger";

export interface GridLocation {
  location_id: number;
  x: number;
  y: number;
  kind: LocationKind;
  zone: string | null;
  aisle: string | null;
}

export type GridTaskStatus = "open" | "assigned" | "picked" | "exception";

export interface GridTask {
  task_id: number;
  order_id: number;
  status: GridTaskStatus;
  priority: number;
  version: number;
  location: GridLocation;
  current_assignment: { assignment_id: number; worker_id: number } | null;
}

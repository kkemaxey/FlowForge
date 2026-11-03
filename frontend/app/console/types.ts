// Shapes of the backend rows the grid map and controls use (snake_case, as the API returns them).

export type LocationKind = "storage" | "pick_station" | "dock" | "charger";

export interface GridLocation {
  location_id: number;
  x: number;
  y: number;
  kind: LocationKind;
  zone: string | null;
  aisle: string | null;
}

export type WorkerKind = "human" | "robot";
export type WorkerStatus = "idle" | "busy" | "down";

export interface GridWorker {
  id: number;
  name: string;
  kind: WorkerKind;
  status: WorkerStatus;
  is_active: boolean;
  x: number;
  y: number;
}

export type TaskStatus = "open" | "assigned" | "picked" | "exception";

export interface GridTask {
  task_id: number;
  order_id: number;
  status: TaskStatus;
  priority: number;
  version: number;
  location: { location_id: number; x: number; y: number; zone: string | null; aisle: string | null };
  current_assignment: { assignment_id: number; worker_id: number } | null;
}

// Shared types that mirror the backend schemas. Add Order, Task and Worker here in Sprint 1.

export type TaskStatus = "open" | "assigned" | "picked" | "complete";

export type WorkerStatus = "idle" | "busy";

// users.role. "supervisor" matches the course spec; "admin" adds the Setup pages.
export type Role = "admin" | "supervisor";

// What a grid cell is used for. Only "storage" cells hold a location (at most one per cell).
// MVP travel time uses Manhattan distance and ignores cell types; pathfinding can use them later.
export type CellType = "storage" | "aisle" | "station" | "blocked";

// A storage slot, e.g. "A1-03". Codes are unique per warehouse, and (warehouse_id, x, y) is unique.
export interface WarehouseLocation {
  code: string;
  x: number;
  y: number;
}

// warehouses row. cells is the layout JSON column: row-major, so cell (x, y) is cells[y * width + x].
export interface Warehouse {
  id: number;
  name: string;
  width: number; // 5 to 60 cells
  height: number; // 5 to 40 cells
  cell_size_m: number; // real-world size of one cell; 1.0 for MVP
  cells: CellType[];
  locations: WarehouseLocation[];
}

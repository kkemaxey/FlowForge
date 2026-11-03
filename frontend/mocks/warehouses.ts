import { notFound } from "next/navigation";

import type { CellType, Warehouse, WarehouseLocation } from "@/types";

import warehouseMap from "./warehouse-map.json";

// Mock warehouses for the wireframes (no backend calls yet).
//
// Warehouse 1 loads warehouse-map.json, a stand-in for the instructor's 20 x 12 map; swap in the real file
// when we get it. Warehouses 2 and 3 are generated at the smallest and largest allowed sizes so we can
// check the grid renders at 5 x 5 and 60 x 40.

/** Aisle letters A..Z, then AA, AB, ... for wide warehouses. */
function aisleLetter(index: number): string {
  const letter = String.fromCharCode(65 + (index % 26));
  return index < 26 ? letter : aisleLetter(Math.floor(index / 26) - 1) + letter;
}

/**
 * A simple pick-face layout: pairs of storage columns separated by one walking aisle, an aisle along the top
 * row, pack/dock stations along the bottom row, and a blocked pillar in the middle of larger floors.
 * Storage cells get codes like "A1-03" (aisle A, side 1, row 03).
 */
export function buildLayout(width: number, height: number): Pick<Warehouse, "cells" | "locations"> {
  const cells: CellType[] = [];
  const locations: WarehouseLocation[] = [];
  const pillar = width >= 10 && height >= 10 ? { x: Math.floor(width / 2), y: Math.floor(height / 2) } : null;

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let type: CellType;
      if (y === height - 1) type = x % 4 === 1 ? "station" : "aisle";
      else if (y === 0 || x % 3 === 2) type = "aisle";
      else if (pillar && x === pillar.x && y === pillar.y) type = "blocked";
      else type = "storage";

      cells.push(type);
      if (type === "storage") {
        const code = `${aisleLetter(Math.floor(x / 3))}${(x % 3) + 1}-${String(y).padStart(2, "0")}`;
        locations.push({ code, x, y });
      }
    }
  }
  return { cells, locations };
}

export const MOCK_WAREHOUSES: Warehouse[] = [
  { id: 1, ...(warehouseMap as Omit<Warehouse, "id">) },
  { id: 2, name: "Micro-fulfillment pod", width: 5, height: 5, cell_size_m: 1, ...buildLayout(5, 5) },
  { id: 3, name: "Regional DC (max size)", width: 60, height: 40, cell_size_m: 1, ...buildLayout(60, 40) },
];

export function getMockWarehouse(id: number): Warehouse | undefined {
  return MOCK_WAREHOUSES.find((w) => w.id === id);
}

/** Looks up the warehouse in a /w/[id] route param, or shows the 404 page. */
export function warehouseOr404(idParam: string): Warehouse {
  const warehouse = getMockWarehouse(Number(idParam));
  if (!warehouse) notFound();
  return warehouse;
}

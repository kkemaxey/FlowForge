import type { CellType, Warehouse, WarehouseLocation } from "@/types";

// The 10 x 10 demo warehouse the backend seeds (Kanayo's layout, 2026-11-02), so the mock frontend shows the
// same floor, SKUs and workers the real API will return.
//
//   y=0      pick stations at (3,0) and (6,0); the rest is walkway
//   y=1..4   zone A: storage bins in columns 1,2 / 4,5 / 7,8 (aisles A1, A2, A3)
//   y=5..8   zone B: same columns (aisles B1, B2, B3)
//   y=9      open floor where the robots park
// Columns 0, 3, 6 and 9 are walkways. 6 aisles x 8 bins = 48 bins.

export const DEMO_WIDTH = 10;
export const DEMO_HEIGHT = 10;

const STORAGE_COLUMNS = [1, 2, 4, 5, 7, 8];
const STATIONS = [3, 6];

export interface DemoSku {
  id: number; // 1..20, the SKU number used in the bin map
  name: string;
  totalPairs: number;
}

export const DEMO_SKUS: DemoSku[] = [
  { id: 1, name: "Air Jordan 1 High", totalPairs: 12 },
  { id: 2, name: "Air Jordan 4", totalPairs: 9 },
  { id: 3, name: "Nike Air Force 1", totalPairs: 10 },
  { id: 4, name: "Nike Dunk Low", totalPairs: 75 },
  { id: 5, name: "Nike Air Max 90", totalPairs: 29 },
  { id: 6, name: "Adidas Samba", totalPairs: 18 },
  { id: 7, name: "Adidas Ultraboost", totalPairs: 24 },
  { id: 8, name: "Yeezy Boost 350", totalPairs: 52 },
  { id: 9, name: "New Balance 550", totalPairs: 23 },
  { id: 10, name: "New Balance 990v6", totalPairs: 37 },
  { id: 11, name: "Converse Chuck 70", totalPairs: 32 },
  { id: 12, name: "Vans Old Skool", totalPairs: 46 },
  { id: 13, name: "Puma Suede", totalPairs: 15 },
  { id: 14, name: "Asics Gel-Kayano 14", totalPairs: 60 },
  { id: 15, name: "Reebok Club C", totalPairs: 19 },
  { id: 16, name: "Salomon XT-6", totalPairs: 30 },
  { id: 17, name: "Hoka Clifton 9", totalPairs: 64 },
  { id: 18, name: "On Cloud 5", totalPairs: 23 },
  { id: 19, name: "Timberland 6-Inch Boot", totalPairs: 26 },
  { id: 20, name: "Crocs Classic Clog", totalPairs: 20 },
];

// SKU number in each bin, rows y=1..8, columns x = 1, 2, 4, 5, 7, 8. 0 = empty.
// 30 bins are stocked and 18 are empty so the simulator has room to reroute stock.
const BIN_MAP: number[][] = [
  [11, 9, 8, 0, 13, 19],
  [12, 0, 0, 1, 2, 0],
  [14, 12, 2, 0, 16, 2],
  [0, 8, 4, 17, 0, 1],
  [14, 5, 0, 15, 1, 20],
  [4, 3, 0, 3, 0, 0],
  [0, 0, 10, 17, 18, 0],
  [7, 6, 0, 0, 0, 0],
];

export interface DemoWorker {
  id: number;
  name: string;
  kind: "human" | "robot";
  x: number;
  y: number;
}

// Starting positions. Sam and Jordan start on the pick stations.
export const DEMO_WORKERS: DemoWorker[] = [
  { id: 1, name: "Alex", kind: "human", x: 0, y: 0 },
  { id: 2, name: "Sam", kind: "human", x: 3, y: 0 },
  { id: 3, name: "Jordan", kind: "human", x: 6, y: 0 },
  { id: 4, name: "Taylor", kind: "human", x: 9, y: 0 },
  { id: 5, name: "Morgan", kind: "human", x: 3, y: 4 },
  { id: 6, name: "Robo-1", kind: "robot", x: 0, y: 9 },
  { id: 7, name: "Robo-2", kind: "robot", x: 3, y: 9 },
  { id: 8, name: "Robo-3", kind: "robot", x: 6, y: 9 },
  { id: 9, name: "Robo-4", kind: "robot", x: 9, y: 9 },
  { id: 10, name: "Robo-5", kind: "robot", x: 6, y: 5 },
];

/**
 * Bin code like "A1-03": zone (A front, B back), aisle 1..3, then bin 01..08 counted front to back,
 * left column odd and right column even.
 */
function binCode(x: number, y: number): string {
  const col = STORAGE_COLUMNS.indexOf(x);
  const zone = y <= 4 ? "A" : "B";
  const aisle = Math.floor(col / 2) + 1;
  const bin = ((y - 1) % 4) * 2 + (col % 2) + 1;
  return `${zone}${aisle}-${String(bin).padStart(2, "0")}`;
}

export interface DemoStock {
  code: string;
  x: number;
  y: number;
  skuId: number;
  pairs: number;
}

/**
 * Every stocked bin. A SKU's pairs are split evenly across its bins (the first bins get the remainder),
 * which gives the 4/4/4, 3/3/3 and 5/5 splits for SKUs 1-3.
 */
export const DEMO_STOCK: DemoStock[] = (() => {
  const bins = BIN_MAP.flatMap((row, i) =>
    row.map((skuId, col) => ({ x: STORAGE_COLUMNS[col], y: i + 1, skuId })).filter((b) => b.skuId !== 0),
  );
  return bins.map((b) => {
    const sku = DEMO_SKUS[b.skuId - 1];
    const sameSku = bins.filter((o) => o.skuId === b.skuId);
    const index = sameSku.indexOf(b);
    const base = Math.floor(sku.totalPairs / sameSku.length);
    const pairs = base + (index < sku.totalPairs % sameSku.length ? 1 : 0);
    return { code: binCode(b.x, b.y), x: b.x, y: b.y, skuId: b.skuId, pairs };
  });
})();

export function buildDemoWarehouse(id: number): Warehouse {
  const cells: CellType[] = [];
  const locations: WarehouseLocation[] = [];
  for (let y = 0; y < DEMO_HEIGHT; y++) {
    for (let x = 0; x < DEMO_WIDTH; x++) {
      const isStorage = y >= 1 && y <= 8 && STORAGE_COLUMNS.includes(x);
      const isStation = y === 0 && STATIONS.includes(x);
      cells.push(isStorage ? "storage" : isStation ? "station" : "aisle");
      if (isStorage) locations.push({ code: binCode(x, y), x, y });
    }
  }
  return { id, name: "Main DC (10 × 10 demo)", width: DEMO_WIDTH, height: DEMO_HEIGHT, cell_size_m: 1, cells, locations };
}

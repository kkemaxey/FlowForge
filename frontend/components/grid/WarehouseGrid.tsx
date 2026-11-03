import type { CellType, Warehouse } from "@/types";

// Draws any warehouse floor from { width, height, cells[] }, from 5 x 5 up to 60 x 40. Cells are square
// and the grid scales to fit its container. Cell types differ in color AND shade/pattern (blocked cells are
// hatched, stations are the darkest), with a legend that spells them out, so nothing relies on color alone.
//
// Shared component: the console's grid map (Aalan) can layer workers and tasks on top of it, and the
// layout editor can reuse it for painting.

const CELL_STYLE: Record<CellType, string> = {
  storage: "bg-blue-300 dark:bg-blue-700",
  aisle: "bg-white dark:bg-zinc-950",
  station: "bg-orange-600 dark:bg-orange-400",
  blocked:
    "bg-red-50 bg-[repeating-linear-gradient(45deg,#dc2626_0_1px,transparent_1px_4px)] dark:bg-red-950",
};

const LEGEND: { type: CellType; label: string }[] = [
  { type: "storage", label: "Storage (one location)" },
  { type: "aisle", label: "Aisle (walkable)" },
  { type: "station", label: "Station (pack/dock)" },
  { type: "blocked", label: "Blocked" },
];

// Small grids would be huge at full width, so cap each cell at about 2.5rem.
const MAX_CELL_REM = 2.5;

export function WarehouseGrid({ warehouse }: { warehouse: Pick<Warehouse, "width" | "height" | "cell_size_m" | "cells" | "locations"> }) {
  const { width, height, cell_size_m, cells, locations } = warehouse;
  const counts = Object.fromEntries(LEGEND.map(({ type }) => [type, 0])) as Record<CellType, number>;
  for (const type of cells) counts[type]++;
  const codeAt = new Map(locations.map((l) => [l.y * width + l.x, l.code]));

  const size = `${width} × ${height} cells · 1 cell = ${cell_size_m} m × ${cell_size_m} m · floor ${width * cell_size_m} m × ${height * cell_size_m} m`;
  const summary = `Warehouse grid, ${size}. ${LEGEND.map(({ type }) => `${counts[type]} ${type}`).join(", ")}.`;

  return (
    <figure className="flex flex-col gap-2">
      <div
        role="img"
        aria-label={summary}
        className="grid w-full gap-px border border-blue-200 bg-blue-100 dark:border-blue-900 dark:bg-blue-950"
        style={{
          gridTemplateColumns: `repeat(${width}, minmax(0, 1fr))`,
          aspectRatio: `${width} / ${height}`,
          maxWidth: `${width * MAX_CELL_REM}rem`,
        }}
      >
        {cells.map((type, i) => {
          const x = i % width;
          const y = Math.floor(i / width);
          const code = codeAt.get(i);
          return <div key={i} className={CELL_STYLE[type]} title={`(${x}, ${y}) ${code ?? type}`} />;
        })}
      </div>
      <figcaption className="flex flex-col gap-1.5 text-xs text-zinc-600 dark:text-zinc-400">
        <span>{size}</span>
        <ul className="flex flex-wrap gap-x-4 gap-y-1">
          {LEGEND.map(({ type, label }) => (
            <li key={type} className="flex items-center gap-1.5">
              <span aria-hidden className={`h-3 w-3 border border-zinc-400 ${CELL_STYLE[type]}`} />
              {label} · {counts[type]}
            </li>
          ))}
        </ul>
      </figcaption>
    </figure>
  );
}

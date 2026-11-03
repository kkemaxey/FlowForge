"use client";

import type { KeyboardEvent } from "react";

import type { CellType, Warehouse } from "@/types";
import type { ConceptWorker } from "@/mocks/conceptMocks";

// The console map as a scalable SVG instead of a CSS grid, so markers, travel paths and a congestion layer can
// sit on top of the floor. Cell colours match WarehouseGrid; workers keep Aalan's shape rule (round = human,
// square = robot) and the workforce status colours. Every marker has a text label and is focusable.

export interface FloorLayers {
  workers: boolean;
  paths: boolean;
  heat: boolean;
  codes: boolean;
}

const CELL = 10;
const GAP = 0.5;

const CELL_FILL: Record<CellType, string> = {
  storage: "fill-blue-300 dark:fill-blue-950",
  aisle: "fill-white dark:fill-zinc-950",
  station: "fill-orange-600 dark:fill-orange-500",
  blocked: "fill-red-100 dark:fill-red-950",
};

const STATUS_FILL: Record<ConceptWorker["status"], string> = {
  idle: "fill-emerald-500",
  busy: "fill-blue-600 dark:fill-blue-500",
  down: "fill-red-600",
  offline: "fill-zinc-400 dark:fill-zinc-600",
};

const STATUS_STROKE: Record<ConceptWorker["status"], string> = {
  idle: "stroke-emerald-600",
  busy: "stroke-blue-600 dark:stroke-blue-400",
  down: "stroke-red-600",
  offline: "stroke-zinc-400",
};

const center = (v: number) => v * CELL + CELL / 2;

/** Walk along the worker's aisle column to the bin's row, then step across into the bin. */
function pathPoints(w: ConceptWorker): string {
  if (!w.task) return "";
  const { x, y } = w.task.target;
  return [`${center(w.x)},${center(w.y)}`, `${center(w.x)},${center(y)}`, `${center(x)},${center(y)}`].join(" ");
}

export function FloorMap({
  warehouse,
  workers,
  congestion,
  stockouts,
  layers,
  selectedId,
  onSelect,
}: {
  warehouse: Pick<Warehouse, "width" | "height" | "cells" | "locations">;
  workers: ConceptWorker[];
  congestion: Record<string, number>;
  stockouts: { x: number; y: number }[];
  layers: FloorLayers;
  selectedId: number | null;
  onSelect: (id: number | null) => void;
}) {
  const { width, height, cells, locations } = warehouse;
  const codeAt = new Map(locations.map((l) => [`${l.x},${l.y}`, l.code]));
  const pad = 6; // room for the axis labels
  const vbW = width * CELL + pad;
  const vbH = height * CELL + pad;
  const selected = workers.find((w) => w.id === selectedId);

  const key = (id: number) => (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSelect(id === selectedId ? null : id);
    }
  };

  return (
    <svg
      viewBox={`${-pad} ${-pad} ${vbW} ${vbH}`}
      className="h-auto w-full max-w-[42rem] select-none"
      role="group"
      aria-label={`Floor map, ${width} by ${height} cells, ${workers.length} workers`}
    >
      <defs>
        <pattern id="ff-hatch" width="2" height="2" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1="0" y1="0" x2="0" y2="2" className="stroke-red-500" strokeWidth="0.6" />
        </pattern>
        <marker id="ff-arrow" viewBox="0 0 6 6" refX="3" refY="3" markerWidth="4" markerHeight="4" orient="auto">
          <path d="M0,0 L6,3 L0,6 z" className="fill-blue-600 dark:fill-blue-400" />
        </marker>
      </defs>

      {/* Axis labels */}
      {Array.from({ length: width }, (_, x) => (
        <text key={`x${x}`} x={center(x)} y={-2} textAnchor="middle" className="fill-zinc-400 text-[3px]">
          {x}
        </text>
      ))}
      {Array.from({ length: height }, (_, y) => (
        <text key={`y${y}`} x={-2.5} y={center(y) + 1} textAnchor="middle" className="fill-zinc-400 text-[3px]">
          {y}
        </text>
      ))}

      {/* Floor */}
      <rect x={-GAP} y={-GAP} width={width * CELL + GAP} height={height * CELL + GAP} className="fill-blue-100 dark:fill-blue-900" />
      {cells.map((type, i) => {
        const x = i % width;
        const y = Math.floor(i / width);
        return (
          <g key={i}>
            <rect x={x * CELL + GAP / 2} y={y * CELL + GAP / 2} width={CELL - GAP} height={CELL - GAP} className={CELL_FILL[type]}>
              <title>{`(${x}, ${y}) ${codeAt.get(`${x},${y}`) ?? type}`}</title>
            </rect>
            {type === "blocked" && <rect x={x * CELL} y={y * CELL} width={CELL} height={CELL} fill="url(#ff-hatch)" />}
            {type === "station" && (
              <text x={x * CELL + 1.2} y={y * CELL + 3.2} className="fill-white text-[2.6px] font-semibold">
                {`P${x === 3 ? 1 : 2}`}
              </text>
            )}
            {layers.codes && type === "storage" && (
              <text x={center(x)} y={y * CELL + 3.2} textAnchor="middle" className="fill-blue-900/70 text-[2.2px] dark:fill-blue-100/70">
                {codeAt.get(`${x},${y}`)}
              </text>
            )}
          </g>
        );
      })}

      {/* Congestion heat on walkable cells */}
      {layers.heat &&
        Object.entries(congestion).map(([k, v]) => {
          const [x, y] = k.split(",").map(Number);
          return (
            <rect
              key={`h${k}`}
              x={x * CELL + GAP / 2}
              y={y * CELL + GAP / 2}
              width={CELL - GAP}
              height={CELL - GAP}
              className="fill-red-500"
              opacity={0.12 + v * 0.5}
            >
              <title>{`Congestion at (${x}, ${y}): ${Math.round(v * 100)}%`}</title>
            </rect>
          );
        })}

      {/* Stockout bins */}
      {stockouts.map(({ x, y }) => (
        <g key={`s${x},${y}`}>
          <rect
            x={x * CELL + 1}
            y={y * CELL + 1}
            width={CELL - 2}
            height={CELL - 2}
            rx={1}
            className="fill-none stroke-red-600"
            strokeWidth={0.9}
            strokeDasharray="1.6 1"
          />
          <text x={center(x)} y={center(y) + 1.6} textAnchor="middle" className="fill-red-700 text-[4.5px] font-bold dark:fill-red-300">
            !
          </text>
        </g>
      ))}

      {/* Travel paths to each task's bin */}
      {layers.paths &&
        workers
          .filter((w) => w.task && w.status === "busy" && w.task.status !== "exception")
          .map((w) => (
            <g key={`p${w.id}`} opacity={selectedId === null || selectedId === w.id ? 1 : 0.25}>
              <polyline
                points={pathPoints(w)}
                fill="none"
                className="stroke-blue-600 dark:stroke-blue-400"
                strokeWidth={0.7}
                strokeDasharray="1.4 1"
                markerEnd="url(#ff-arrow)"
              />
              <rect
                x={w.task!.target.x * CELL + 1.2}
                y={w.task!.target.y * CELL + 1.2}
                width={CELL - 2.4}
                height={CELL - 2.4}
                rx={1}
                className="fill-none stroke-blue-700 dark:stroke-blue-300"
                strokeWidth={0.6}
              />
            </g>
          ))}

      {/* Workers */}
      {layers.workers &&
        workers.map((w) => {
          const cx = center(w.x);
          const cy = center(w.y);
          const isSel = w.id === selectedId;
          const label = `${w.name}, ${w.kind}, ${w.status}${w.task ? `, task ${w.task.id}` : ""}`;
          const dim = selectedId !== null && !isSel ? 0.6 : 1;
          return (
            <g
              key={w.id}
              role="button"
              tabIndex={0}
              aria-label={label}
              aria-pressed={isSel}
              onClick={() => onSelect(isSel ? null : w.id)}
              onKeyDown={key(w.id)}
              className="cursor-pointer outline-none [&:focus-visible>.ring]:opacity-100"
              opacity={dim}
            >
              <title>{label}</title>
              <circle cx={cx} cy={cy} r={4.8} className={`ring fill-none ${STATUS_STROKE[w.status]} ${isSel ? "opacity-100" : "opacity-0"}`} strokeWidth={0.7} />
              {w.kind === "human" ? (
                <circle cx={cx} cy={cy} r={3.3} className={`${STATUS_FILL[w.status]} stroke-white dark:stroke-zinc-950`} strokeWidth={0.5} />
              ) : (
                <rect x={cx - 3.1} y={cy - 3.1} width={6.2} height={6.2} rx={1.1} className={`${STATUS_FILL[w.status]} stroke-white dark:stroke-zinc-950`} strokeWidth={0.5} />
              )}
              <text x={cx} y={cy + 1.25} textAnchor="middle" className="pointer-events-none fill-white text-[3.4px] font-bold">
                {w.kind === "robot" ? `R${w.name.split("-")[1]}` : w.name[0]}
              </text>
              {w.status === "down" && <line x1={cx - 3} y1={cy + 3} x2={cx + 3} y2={cy - 3} className="stroke-white" strokeWidth={0.6} />}
            </g>
          );
        })}

      {/* Selected worker's name tag */}
      {selected && layers.workers && (
        <g className="pointer-events-none">
          <rect
            x={Math.min(center(selected.x) - 9, width * CELL - 18)}
            y={center(selected.y) - 11.5}
            width={18}
            height={5}
            rx={1}
            className="fill-zinc-900 dark:fill-zinc-100"
          />
          <text
            x={Math.min(center(selected.x), width * CELL - 9)}
            y={center(selected.y) - 8}
            textAnchor="middle"
            className="fill-white text-[3px] font-medium dark:fill-zinc-900"
          >
            {selected.name}
          </text>
        </g>
      )}
    </svg>
  );
}

export function FloorLegend() {
  const item = "flex items-center gap-1.5";
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-600 dark:text-zinc-400">
      <li className={item}>
        <span aria-hidden className="h-3 w-3 rounded-full bg-blue-600" /> Human
      </li>
      <li className={item}>
        <span aria-hidden className="h-3 w-3 rounded-sm bg-blue-600" /> Robot
      </li>
      <li className={item}>
        <span aria-hidden className="h-3 w-3 rounded-full bg-emerald-500" /> Idle
      </li>
      <li className={item}>
        <span aria-hidden className="h-3 w-3 rounded-full bg-blue-600" /> Busy
      </li>
      <li className={item}>
        <span aria-hidden className="h-3 w-3 rounded-full bg-red-600" /> Down (struck through)
      </li>
      <li className={item}>
        <span aria-hidden className="h-3 w-3 rounded-full bg-zinc-400" /> Offline
      </li>
      <li className={item}>
        <span aria-hidden className="h-3 w-3 border border-dashed border-red-600 text-center text-[8px] leading-[10px] font-bold text-red-700">!</span> Stockout bin
      </li>
      <li className={item}>
        <span aria-hidden className="h-0 w-4 border-t border-dashed border-blue-600" /> Path to bin
      </li>
      <li className={item}>
        <span aria-hidden className="h-3 w-3 bg-red-500/50" /> Congestion
      </li>
    </ul>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";

import { Badge, BUTTON, FIELD, Kbd, Panel, PRIMARY_BUTTON } from "@/components/concepts/ConceptKit";
import { DEMO_SKUS, DEMO_STOCK, DEMO_WAREHOUSE } from "@/mocks/demoWarehouse";
import type { CellType } from "@/types";

// Paintable layout editor. Validation runs on every stroke so the admin sees the problem where they made it,
// and Publish stays disabled while anything blocks it. Saving would PUT the whole layout as one new version.

const { width: W, height: H } = DEMO_WAREHOUSE;
const SAVED = DEMO_WAREHOUSE.cells;

const CELL_CLASS: Record<CellType, string> = {
  storage: "bg-blue-300 dark:bg-blue-700",
  aisle: "bg-white dark:bg-zinc-950",
  station: "bg-orange-600 dark:bg-orange-400",
  blocked: "bg-red-50 bg-[repeating-linear-gradient(45deg,#dc2626_0_1px,transparent_1px_4px)] dark:bg-red-950",
};

const TOOLS: { type: CellType; label: string; key: string }[] = [
  { type: "storage", label: "Storage", key: "1" },
  { type: "aisle", label: "Aisle", key: "2" },
  { type: "station", label: "Station", key: "3" },
  { type: "blocked", label: "Blocked", key: "4" },
];

const codeAt = new Map(DEMO_WAREHOUSE.locations.map((l) => [l.y * W + l.x, l.code]));
const stockAt = new Map(DEMO_STOCK.map((s) => [s.y * W + s.x, s]));

interface Issue {
  level: "error" | "warning";
  cells: number[];
  text: string;
}

const walkable = (t: CellType) => t === "aisle" || t === "station";
const neighbours = (i: number) => {
  const x = i % W;
  const y = Math.floor(i / W);
  return [
    [x - 1, y],
    [x + 1, y],
    [x, y - 1],
    [x, y + 1],
  ]
    .filter(([nx, ny]) => nx >= 0 && ny >= 0 && nx < W && ny < H)
    .map(([nx, ny]) => ny * W + nx);
};
const xy = (i: number) => `(${i % W}, ${Math.floor(i / W)})`;

function validate(cells: CellType[]): Issue[] {
  const issues: Issue[] = [];
  const stations = cells.flatMap((t, i) => (t === "station" ? [i] : []));
  if (stations.length === 0) issues.push({ level: "error", cells: [], text: "No pick station. Orders need at least one station to drop at." });

  // Everything reachable on foot from any station.
  const seen = new Set<number>(stations);
  const queue = [...stations];
  while (queue.length) {
    const i = queue.shift()!;
    for (const n of neighbours(i)) {
      if (seen.has(n) || !walkable(cells[n])) continue;
      seen.add(n);
      queue.push(n);
    }
  }

  const unreachable = cells.flatMap((t, i) => (t === "storage" && !neighbours(i).some((n) => seen.has(n)) ? [i] : []));
  if (stations.length && unreachable.length)
    issues.push({
      level: "error",
      cells: unreachable,
      text: `${unreachable.length} storage cell${unreachable.length > 1 ? "s" : ""} can't be reached from a station: ${unreachable.slice(0, 4).map((i) => codeAt.get(i) ?? xy(i)).join(", ")}${unreachable.length > 4 ? "…" : ""}`,
    });

  const lostStock = [...stockAt.entries()].filter(([i]) => cells[i] !== "storage");
  for (const [i, s] of lostStock)
    issues.push({ level: "error", cells: [i], text: `${s.code} holds ${s.pairs} pairs of ${DEMO_SKUS[s.skuId - 1].name}. Move the stock before changing this cell.` });

  const islands = cells.flatMap((t, i) => (t === "aisle" && stations.length && !seen.has(i) ? [i] : []));
  if (islands.length) issues.push({ level: "warning", cells: islands, text: `${islands.length} aisle cell${islands.length > 1 ? "s are" : " is"} cut off from the stations.` });

  const newBins = cells.flatMap((t, i) => (t === "storage" && SAVED[i] !== "storage" ? [i] : []));
  if (newBins.length) issues.push({ level: "warning", cells: newBins, text: `${newBins.length} new storage cell${newBins.length > 1 ? "s" : ""} will get codes on publish (next free code per aisle).` });
  return issues;
}

export function LayoutEditor() {
  const [cells, setCells] = useState<CellType[]>(SAVED);
  const [history, setHistory] = useState<CellType[][]>([]);
  const [tool, setTool] = useState<CellType>("blocked");
  const [painting, setPainting] = useState(false);
  const [selected, setSelected] = useState<number | null>(null);
  const [hoverIssue, setHoverIssue] = useState<number[] | null>(null);
  const [published, setPublished] = useState(false);

  const issues = useMemo(() => validate(cells), [cells]);
  const errors = issues.filter((i) => i.level === "error");
  const changed = cells.reduce((n, t, i) => n + (t !== SAVED[i] ? 1 : 0), 0);
  const problemCells = new Set(errors.flatMap((e) => e.cells));
  const highlight = new Set(hoverIssue ?? []);

  useEffect(() => {
    const stop = () => setPainting(false);
    const keys = (e: KeyboardEvent) => {
      if ((e.target as HTMLElement).tagName === "INPUT") return;
      const t = TOOLS.find((tool) => tool.key === e.key);
      if (t) setTool(t.type);
    };
    window.addEventListener("pointerup", stop);
    window.addEventListener("keydown", keys);
    return () => {
      window.removeEventListener("pointerup", stop);
      window.removeEventListener("keydown", keys);
    };
  }, []);

  function paint(i: number, startStroke = false) {
    if (cells[i] === tool) return;
    if (startStroke) setHistory((h) => [...h.slice(-19), cells]);
    setCells((c) => c.map((t, j) => (j === i ? tool : t)));
    setPublished(false);
  }

  function undo() {
    if (!history.length) return;
    setCells(history[history.length - 1]);
    setHistory((h) => h.slice(0, -1));
  }

  const sel = selected === null ? null : { i: selected, type: cells[selected], code: codeAt.get(selected), stock: stockAt.get(selected) };
  const counts = TOOLS.map(({ type }) => cells.filter((t) => t === type).length);

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <Panel
        title="Floor plan"
        subtitle={`Draft from v3 · ${changed} cell${changed === 1 ? "" : "s"} changed`}
        actions={
          <>
            <button type="button" className={BUTTON} disabled={!history.length} onClick={undo}>
              ↶ Undo
            </button>
            <button
              type="button"
              className={BUTTON}
              disabled={!changed}
              onClick={() => {
                setHistory((h) => [...h, cells]);
                setCells(SAVED);
              }}
            >
              Discard draft
            </button>
            <button type="button" className={PRIMARY_BUTTON} disabled={!changed || errors.length > 0} onClick={() => setPublished(true)}>
              Publish v4
            </button>
          </>
        }
      >
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <div role="radiogroup" aria-label="Paint with" className="flex flex-wrap gap-1.5">
            {TOOLS.map((t, n) => (
              <button
                key={t.type}
                type="button"
                role="radio"
                aria-checked={tool === t.type}
                onClick={() => setTool(t.type)}
                className={`flex items-center gap-1.5 rounded-md border px-2 py-1 text-xs font-medium ${
                  tool === t.type
                    ? "border-blue-600 bg-blue-50 text-blue-800 dark:border-blue-500 dark:bg-blue-950 dark:text-blue-200"
                    : "border-zinc-300 text-zinc-700 dark:border-zinc-700 dark:text-zinc-300"
                }`}
              >
                <span aria-hidden className={`h-3.5 w-3.5 border border-zinc-400 ${CELL_CLASS[t.type]}`} />
                {t.label}
                <span className="tabular-nums text-zinc-400">{counts[n]}</span>
                <Kbd>{t.key}</Kbd>
              </button>
            ))}
          </div>
          <div className="flex items-center gap-1.5 text-xs text-zinc-500">
            <label className="flex items-center gap-1">
              W <input disabled value={W} className={`${FIELD} w-12 py-0.5 text-xs`} aria-label="Width in cells" />
            </label>
            ×
            <label className="flex items-center gap-1">
              H <input disabled value={H} className={`${FIELD} w-12 py-0.5 text-xs`} aria-label="Height in cells" />
            </label>
            <span>cells · 1 m</span>
          </div>
        </div>

        {published && (
          <p role="status" className="mb-3 rounded-md border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/50 dark:text-emerald-200">
            Mock: v4 would be published. Running sims keep v3 until their next reset.
          </p>
        )}

        <div
          className="grid w-full max-w-[34rem] touch-none gap-px border border-blue-200 bg-blue-100 dark:border-blue-900 dark:bg-blue-950"
          style={{ gridTemplateColumns: `repeat(${W}, minmax(0, 1fr))`, aspectRatio: `${W} / ${H}` }}
          onPointerLeave={() => setPainting(false)}
        >
          {cells.map((type, i) => {
            const changedHere = type !== SAVED[i];
            const code = codeAt.get(i);
            const label = `${xy(i)} ${type}${code && type === "storage" ? ` ${code}` : ""}${changedHere ? ", changed" : ""}${problemCells.has(i) ? ", has a problem" : ""}`;
            return (
              <button
                key={i}
                type="button"
                aria-label={label}
                title={label}
                onPointerDown={(e) => {
                  e.preventDefault();
                  setPainting(true);
                  setSelected(i);
                  paint(i, true);
                }}
                onPointerEnter={() => painting && paint(i)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelected(i);
                    paint(i, true);
                  }
                }}
                onFocus={() => setSelected(i)}
                className={`relative ${CELL_CLASS[type]} outline-none focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-blue-600 ${
                  selected === i ? "z-10 ring-2 ring-zinc-900 dark:ring-zinc-100" : ""
                } ${highlight.has(i) ? "z-10 ring-2 ring-amber-500" : ""}`}
              >
                {changedHere && <span aria-hidden className="absolute top-0.5 left-0.5 h-1.5 w-1.5 rounded-full bg-violet-600" />}
                {problemCells.has(i) && (
                  <span aria-hidden className="absolute inset-0 flex items-center justify-center text-xs font-bold text-red-700 dark:text-red-300">
                    !
                  </span>
                )}
              </button>
            );
          })}
        </div>
        <p className="mt-2 text-xs text-zinc-500">
          Click or drag to paint. <span className="inline-block h-1.5 w-1.5 rounded-full bg-violet-600 align-middle" /> changed since v3 ·{" "}
          <span className="font-bold text-red-700">!</span> blocks publishing. Keys 1–4 switch the brush.
        </p>
      </Panel>

      <div className="flex flex-col gap-4">
        <Panel title="Checks" subtitle={errors.length ? `${errors.length} blocking` : "Ready to publish"} actions={errors.length ? <Badge tone="red">blocked</Badge> : <Badge tone="emerald">ok</Badge>}>
          {issues.length === 0 ? (
            <p className="text-sm text-zinc-500">No problems. Paint a cell to see checks run live.</p>
          ) : (
            <ul className="flex flex-col gap-2 text-xs">
              {issues.map((issue) => (
                <li
                  key={issue.text}
                  onMouseEnter={() => setHoverIssue(issue.cells)}
                  onMouseLeave={() => setHoverIssue(null)}
                  className={`rounded-md border px-2 py-1.5 ${
                    issue.level === "error"
                      ? "border-red-300 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200"
                      : "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200"
                  }`}
                >
                  <span className="font-semibold">{issue.level === "error" ? "Error" : "Warning"}:</span> {issue.text}
                </li>
              ))}
            </ul>
          )}
          <p className="mt-2 text-[11px] text-zinc-500">Try: paint a blocked wall across column 3, or paint over a stocked bin.</p>
        </Panel>

        <Panel title="Cell" subtitle={sel ? xy(sel.i) : "Nothing selected"}>
          {sel ? (
            <dl className="grid grid-cols-[5rem_1fr] gap-x-2 gap-y-1 text-xs">
              <dt className="text-zinc-500">Type</dt>
              <dd>
                {sel.type}
                {sel.type !== SAVED[sel.i] && <span className="text-violet-700 dark:text-violet-400"> (was {SAVED[sel.i]})</span>}
              </dd>
              <dt className="text-zinc-500">Location</dt>
              <dd className="font-mono">{sel.type === "storage" ? (sel.code ?? "new, coded on publish") : "—"}</dd>
              <dt className="text-zinc-500">Stock</dt>
              <dd>{sel.stock ? `${sel.stock.pairs} pairs · ${DEMO_SKUS[sel.stock.skuId - 1].name}` : "Empty"}</dd>
            </dl>
          ) : (
            <p className="text-xs text-zinc-500">Click a cell to see its location code and stock.</p>
          )}
        </Panel>

        <Panel title="Versions">
          <ol className="flex flex-col gap-1.5 text-xs">
            <li className="flex justify-between">
              <span>
                <span className="font-semibold">Draft</span> · {changed} changes
              </span>
              <span className="text-zinc-500">unsaved</span>
            </li>
            {[
              ["v3", "Live · 48 bins, 2 stations", "Nov 2 · Kanayo"],
              ["v2", "Moved station P2 to (6, 0)", "Oct 28 · Aalan"],
              ["v1", "Seed layout", "Oct 20 · Kanayo"],
            ].map(([v, what, when]) => (
              <li key={v} className="flex justify-between gap-2">
                <span>
                  <span className="font-mono font-semibold">{v}</span> · {what}
                </span>
                <span className="shrink-0 text-zinc-500">{when}</span>
              </li>
            ))}
          </ol>
          <div className="mt-3 flex gap-1.5">
            <button type="button" className={BUTTON}>
              Import JSON
            </button>
            <button type="button" className={BUTTON}>
              Export JSON
            </button>
          </div>
        </Panel>
      </div>
    </div>
  );
}

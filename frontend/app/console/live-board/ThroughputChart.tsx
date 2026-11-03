"use client";

import { useEffect, useState } from "react";

import { Card } from "@/components/ui/Card";

import { getThroughput, type ThroughputBucket } from "./data";
import { summarizeThroughput } from "./boardLogic";

// Throughput over time for the metrics page: units picked per minute over the last 30 minutes, as a
// blue bar chart. A one-line summary and a data table sit underneath so the numbers are readable
// without the chart (screen readers, or anyone who wants exact values).

const MINUTES = 30;
const REFRESH_MS = 10_000; // the newest bucket fills in over the minute, so refresh it every 10 s

// Chart geometry in SVG units; the SVG scales to its container width.
const W = 600;
const H = 180;
const PAD = { top: 10, right: 8, bottom: 22, left: 32 };

const formatMinute = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });

export function ThroughputChart() {
  const [buckets, setBuckets] = useState<ThroughputBucket[] | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const next = await getThroughput(MINUTES);
        if (!cancelled) {
          setBuckets(next);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err : new Error(String(err)));
      }
    }
    load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <Card title={`Throughput · last ${MINUTES} minutes`}>
      {!buckets && !error && <p className="text-sm text-zinc-500">Loading throughput…</p>}
      {!buckets && error && (
        <p className="text-sm text-zinc-700 dark:text-zinc-300">
          Couldn&apos;t load throughput. The chart needs a throughput endpoint, which the backend doesn&apos;t have yet.
        </p>
      )}
      {buckets && <ChartBody buckets={buckets} />}
    </Card>
  );
}

function ChartBody({ buckets }: { buckets: ThroughputBucket[] }) {
  const { totalUnits, unitsPerHour, peak } = summarizeThroughput(buckets);
  const max = Math.max(1, ...buckets.map((b) => b.units));
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const slot = plotW / buckets.length;
  const summary =
    `${totalUnits.toLocaleString()} units in the last ${buckets.length} minutes (about ${unitsPerHour.toLocaleString()} units/hr)` +
    (peak ? `. Busiest minute: ${formatMinute(peak.bucket_start)} with ${peak.units} units.` : ".");

  return (
    <div className="flex flex-col gap-3">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label={`Bar chart. ${summary}`}>
        {/* Gridlines at 0, half and max, labelled on the left */}
        {[0, 0.5, 1].map((f) => {
          const y = PAD.top + plotH * (1 - f);
          return (
            <g key={f}>
              <line x1={PAD.left} x2={W - PAD.right} y1={y} y2={y} className="stroke-zinc-200 dark:stroke-zinc-800" />
              <text x={PAD.left - 6} y={y + 3} textAnchor="end" className="fill-zinc-500 text-[10px]">
                {Math.round(max * f)}
              </text>
            </g>
          );
        })}
        {buckets.map((b, i) => {
          const h = (b.units / max) * plotH;
          const x = PAD.left + i * slot;
          const latest = i === buckets.length - 1;
          return (
            <g key={b.bucket_start}>
              <rect
                x={x + slot * 0.15}
                y={PAD.top + plotH - h}
                width={slot * 0.7}
                height={h}
                // The current minute is still filling, so it's drawn hollow rather than solid.
                className={latest ? "fill-blue-50 stroke-blue-600 dark:fill-blue-950 dark:stroke-blue-400" : "fill-blue-600 dark:fill-blue-400"}
              >
                <title>{`${formatMinute(b.bucket_start)}: ${b.units} units, ${b.tasks} tasks`}</title>
              </rect>
              {i % 5 === 0 && (
                <text x={x + slot / 2} y={H - 6} textAnchor="middle" className="fill-zinc-500 text-[10px]">
                  {formatMinute(b.bucket_start)}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">{summary} The hollow bar is the current minute.</p>
      <details className="text-sm">
        <summary className="cursor-pointer text-zinc-600 dark:text-zinc-400">Show data table</summary>
        <div className="mt-2 max-h-64 overflow-auto rounded-md border border-zinc-200 dark:border-zinc-800">
          <table className="w-full text-left">
            <thead className="sticky top-0 bg-zinc-50 text-xs text-zinc-500 dark:bg-zinc-900">
              <tr>
                <th className="px-3 py-1.5 font-medium">Minute</th>
                <th className="px-3 py-1.5 text-right font-medium">Units</th>
                <th className="px-3 py-1.5 text-right font-medium">Tasks</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200 tabular-nums dark:divide-zinc-800">
              {buckets.map((b) => (
                <tr key={b.bucket_start}>
                  <td className="px-3 py-1">{formatMinute(b.bucket_start)}</td>
                  <td className="px-3 py-1 text-right">{b.units}</td>
                  <td className="px-3 py-1 text-right">{b.tasks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}

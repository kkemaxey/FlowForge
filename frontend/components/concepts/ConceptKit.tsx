import type { ReactNode } from "react";

// Shared pieces for the /concepts pages: future-state wireframes that sit next to the low-fidelity ones.
// They reuse the portal palette (zinc neutrals, blue-600 primary, orange WIP, emerald on-time, red
// exceptions, amber notes) so a concept can be lifted into the real page without a restyle.

export type Tone = "neutral" | "blue" | "orange" | "emerald" | "red" | "amber" | "violet";

export const TONE_TEXT: Record<Tone, string> = {
  neutral: "text-zinc-700 dark:text-zinc-300",
  blue: "text-blue-700 dark:text-blue-400",
  orange: "text-orange-700 dark:text-orange-400",
  emerald: "text-emerald-700 dark:text-emerald-400",
  red: "text-red-700 dark:text-red-400",
  amber: "text-amber-700 dark:text-amber-400",
  violet: "text-violet-700 dark:text-violet-400",
};

export const TONE_BADGE: Record<Tone, string> = {
  neutral: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  blue: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  orange: "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300",
  emerald: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  red: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
  amber: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  violet: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300",
};

const TONE_STROKE: Record<Tone, string> = {
  neutral: "stroke-zinc-500",
  blue: "stroke-blue-600 dark:stroke-blue-400",
  orange: "stroke-orange-500 dark:stroke-orange-400",
  emerald: "stroke-emerald-600 dark:stroke-emerald-400",
  red: "stroke-red-600 dark:stroke-red-400",
  amber: "stroke-amber-500 dark:stroke-amber-400",
  violet: "stroke-violet-600 dark:stroke-violet-400",
};

const TONE_EDGE: Record<Tone, string> = {
  neutral: "border-l-zinc-400",
  blue: "border-l-blue-600",
  orange: "border-l-orange-500",
  emerald: "border-l-emerald-500",
  red: "border-l-red-600",
  amber: "border-l-amber-500",
  violet: "border-l-violet-500",
};

export const BUTTON =
  "inline-flex items-center justify-center gap-1 rounded-md border border-zinc-300 px-2 py-1 text-xs font-medium text-zinc-700 hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-40 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800";
export const PRIMARY_BUTTON =
  "inline-flex items-center justify-center gap-1 rounded-md bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-400";
export const DANGER_BUTTON =
  "inline-flex items-center justify-center gap-1 rounded-md bg-red-600 px-2 py-1 text-xs font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50";
export const FIELD =
  "rounded-md border border-zinc-300 bg-white px-2 py-1 text-sm text-zinc-900 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100";

/** The strip at the top of each concept page: what it is, when it might ship and what it builds on. */
export function ConceptBanner({ target, buildsOn, children }: { target: string; buildsOn: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col gap-1 rounded-md border border-dashed border-violet-300 bg-violet-50/60 px-3 py-2 text-xs text-violet-900 sm:flex-row sm:items-center sm:justify-between dark:border-violet-800 dark:bg-violet-950/30 dark:text-violet-200">
      <p>
        <span className="mr-1.5 rounded bg-violet-600 px-1.5 py-0.5 font-semibold text-white dark:bg-violet-500">Concept</span>
        {children ?? "Future direction, not wired to the API. Every number on this page is mock data."}
      </p>
      <p className="shrink-0 text-violet-700 dark:text-violet-300">
        Target: <span className="font-semibold">{target}</span> · Builds on {buildsOn}
      </p>
    </div>
  );
}

/** A Card with an optional right-side slot for actions or a status, and an optional subtitle. */
export function Panel({
  title,
  subtitle,
  actions,
  children,
  className = "",
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`flex min-w-0 flex-col rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-950 ${className}`}>
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">{title}</h2>
          {subtitle && <p className="text-xs text-zinc-500">{subtitle}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-1.5">{actions}</div>}
      </div>
      {children}
    </section>
  );
}

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${TONE_BADGE[tone]}`}>{children}</span>;
}

/** A coloured dot that always comes with a text label, so status never relies on colour alone. */
export function StatusDot({ tone, label, pulse = false }: { tone: Tone; label: string; pulse?: boolean }) {
  const bg: Record<Tone, string> = {
    neutral: "bg-zinc-400",
    blue: "bg-blue-600",
    orange: "bg-orange-500",
    emerald: "bg-emerald-500",
    red: "bg-red-600",
    amber: "bg-amber-500",
    violet: "bg-violet-500",
  };
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="relative flex h-2 w-2" aria-hidden>
        {pulse && <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-60 ${bg[tone]}`} />}
        <span className={`relative inline-flex h-2 w-2 rounded-full ${bg[tone]}`} />
      </span>
      {label}
    </span>
  );
}

/** Tiny trend line. Decorative: the tile next to it carries the number in text. */
export function Sparkline({ values, tone = "blue", className = "h-8 w-full" }: { values: number[]; tone?: Tone; className?: string }) {
  const w = 100;
  const h = 30;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const points = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - 2 - ((v - min) / span) * (h - 4)}`).join(" ");
  const last = points.split(" ").at(-1)!.split(",");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" className={className} aria-hidden>
      <polyline points={points} fill="none" strokeWidth={1.5} vectorEffect="non-scaling-stroke" className={TONE_STROKE[tone]} />
      <circle cx={last[0]} cy={last[1]} r={2} className={`${TONE_STROKE[tone]} fill-white dark:fill-zinc-950`} vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

/** KPI tile in the same shape as the live board's, plus a target line and a sparkline. */
export function KpiTile({
  label,
  value,
  unit,
  detail,
  tone,
  trend,
  delta,
}: {
  label: string;
  value: string;
  unit?: string;
  detail: string;
  tone: Tone;
  trend?: number[];
  delta?: { text: string; good: boolean };
}) {
  return (
    <div className={`flex min-w-0 flex-col rounded-md border border-l-4 border-zinc-200 bg-white p-3 dark:border-zinc-800 dark:bg-zinc-950 ${TONE_EDGE[tone]}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-zinc-500">{label}</p>
        {delta && (
          <span className={`text-[11px] font-medium tabular-nums ${delta.good ? "text-emerald-700 dark:text-emerald-400" : "text-red-700 dark:text-red-400"}`}>
            {delta.good ? "▲" : "▼"} {delta.text}
          </span>
        )}
      </div>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-100">
        {value}
        {unit && <span className="ml-1 text-sm font-normal text-zinc-500">{unit}</span>}
      </p>
      {trend && <Sparkline values={trend} tone={tone} className="mt-1 h-7 w-full" />}
      <p className="mt-1 text-xs text-zinc-500">{detail}</p>
    </div>
  );
}

/** Segmented control used for speed, filters and map layers. */
export function Segmented<T extends string>({
  label,
  options,
  value,
  onChange,
  size = "sm",
}: {
  label: string;
  options: { value: T; label: string; disabled?: boolean }[];
  value: T;
  onChange?: (value: T) => void;
  size?: "sm" | "xs";
}) {
  return (
    <div role="group" aria-label={label} className="inline-flex rounded-md border border-zinc-300 p-0.5 dark:border-zinc-700">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={o.value === value}
          disabled={o.disabled}
          onClick={() => onChange?.(o.value)}
          className={`rounded font-medium tabular-nums disabled:cursor-not-allowed disabled:opacity-40 ${size === "xs" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs"} ${
            o.value === value
              ? "bg-blue-600 text-white dark:bg-blue-500"
              : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

/** A horizontal bar with its value in text beside it. */
export function Meter({ value, max = 100, tone = "blue", label }: { value: number; max?: number; tone?: Tone; label?: string }) {
  const fill: Record<Tone, string> = {
    neutral: "bg-zinc-400",
    blue: "bg-blue-600 dark:bg-blue-500",
    orange: "bg-orange-500",
    emerald: "bg-emerald-500",
    red: "bg-red-600",
    amber: "bg-amber-500",
    violet: "bg-violet-500",
  };
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800" aria-hidden>
        <div className={`h-full rounded-full ${fill[tone]}`} style={{ width: `${pct}%` }} />
      </div>
      {label && <span className="w-12 shrink-0 text-right text-xs tabular-nums text-zinc-600 dark:text-zinc-400">{label}</span>}
    </div>
  );
}

/** Keyboard hint, e.g. <Kbd>⌘K</Kbd>. */
export function Kbd({ children }: { children: ReactNode }) {
  return (
    <kbd className="rounded border border-zinc-300 bg-zinc-50 px-1 font-mono text-[10px] text-zinc-600 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400">
      {children}
    </kbd>
  );
}

import type { ReactNode } from "react";

// Building blocks for the low-fidelity wireframe pages: a page header, a collapsible notes panel listing
// each page's rules and who can do what, and dashed boxes standing in for components not built yet.

export interface PageNotes {
  rules: string[];
  supervisor: string;
  admin: string;
}

export function PageHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <header>
      <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">{title}</h1>
      {subtitle && <p className="mt-0.5 text-sm text-zinc-500">{subtitle}</p>}
    </header>
  );
}

export function Annotation({ notes }: { notes: PageNotes }) {
  return (
    <details className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-950/40">
      <summary className="cursor-pointer font-medium text-amber-900 dark:text-amber-200">
        Wireframe notes
      </summary>
      <div className="mt-2 grid gap-3 text-zinc-600 sm:grid-cols-2 dark:text-zinc-400">
        <div>
          <p className="font-medium text-zinc-700 dark:text-zinc-300">Rules</p>
          <ul className="mt-1 list-disc space-y-0.5 pl-5">
            {notes.rules.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>
        </div>
        <dl className="space-y-1">
          <dt className="font-medium text-zinc-700 dark:text-zinc-300">Supervisor</dt>
          <dd>{notes.supervisor}</dd>
          <dt className="font-medium text-zinc-700 dark:text-zinc-300">Admin</dt>
          <dd>{notes.admin}</dd>
        </dl>
      </div>
    </details>
  );
}

export function PlaceholderBox({ label, children, className = "" }: { label: string; children?: ReactNode; className?: string }) {
  return (
    <section
      aria-label={label}
      className={`flex min-h-28 flex-col gap-1 rounded-md border-2 border-dashed border-blue-200 bg-blue-50/40 p-3 text-sm text-zinc-500 dark:border-blue-900 dark:bg-blue-950/20 ${className}`}
    >
      <p className="font-medium text-blue-900 dark:text-blue-200">{label}</p>
      {children}
    </section>
  );
}

/** A whole page that is only a wireframe so far: header, one dashed box per key element, and notes. */
export function PlaceholderPage({
  title,
  subtitle,
  elements,
  notes,
}: {
  title: string;
  subtitle?: string;
  elements: string[];
  notes: PageNotes;
}) {
  return (
    <div className="flex flex-col gap-4">
      <PageHeader title={title} subtitle={subtitle} />
      <div className="grid gap-3 sm:grid-cols-2">
        {elements.map((element) => (
          <PlaceholderBox key={element} label={element} />
        ))}
      </div>
      <Annotation notes={notes} />
    </div>
  );
}

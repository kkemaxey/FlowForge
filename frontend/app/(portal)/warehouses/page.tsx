import { cookies } from "next/headers";
import Link from "next/link";

import { Annotation, PageHeader } from "@/components/portal/Wireframe";
import { parseRole, ROLE_COOKIE } from "@/lib/mockRole";
import { MOCK_WAREHOUSES } from "@/mocks/warehouses";

export default async function WarehousesPage() {
  const role = parseRole((await cookies()).get(ROLE_COOKIE)?.value);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <PageHeader title="Warehouses" subtitle="Pick a site to open its console." />
        {role === "admin" && (
          <Link
            href="/admin/warehouses/new"
            className="rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            + New warehouse
          </Link>
        )}
      </div>
      <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {MOCK_WAREHOUSES.map((w) => (
          <li key={w.id}>
            <Link
              href={`/w/${w.id}/console`}
              className="flex flex-col gap-3 rounded-lg border border-zinc-300 p-4 hover:border-blue-500 dark:border-zinc-700 dark:hover:border-blue-400"
            >
              <div>
                <p className="font-medium text-zinc-900 dark:text-zinc-100">{w.name}</p>
                <p className="text-xs text-zinc-500">
                  {w.width} × {w.height} cells · {w.locations.length} locations
                </p>
              </div>
              <dl className="grid grid-cols-3 gap-2 text-center text-xs text-zinc-500">
                {["Units/hr", "WIP", "On-time"].map((kpi) => (
                  <div key={kpi} className="rounded bg-blue-50 py-2 dark:bg-blue-950">
                    <dd className="text-base font-semibold text-zinc-400">—</dd>
                    <dt>{kpi}</dt>
                  </div>
                ))}
              </dl>
            </Link>
          </li>
        ))}
      </ul>
      <Annotation
        notes={{
          rules: [
            "Card KPIs come from GET /events/metrics?warehouse_id= (dashes until wired).",
            "Optional user_warehouses table can limit which sites a supervisor sees.",
          ],
          supervisor: "Sees and opens the warehouses they have access to.",
          admin: "Sees all warehouses, plus “+ New warehouse”.",
        }}
      />
    </div>
  );
}

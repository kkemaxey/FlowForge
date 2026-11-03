import { cookies } from "next/headers";
import Link from "next/link";
import type { ReactNode } from "react";

import { PortalNav } from "@/components/portal/PortalNav";
import { RoleToggle } from "@/components/portal/RoleToggle";
import { parseRole, ROLE_COOKIE, ROLE_TOGGLE_ENABLED } from "@/lib/mockRole";
import { MOCK_WAREHOUSES } from "@/mocks/warehouses";

// The one nav shell every portal page shares. Admin view = supervisor view + the Setup section.
export default async function PortalLayout({ children }: { children: ReactNode }) {
  const role = parseRole((await cookies()).get(ROLE_COOKIE)?.value);
  const warehouses = MOCK_WAREHOUSES.map(({ id, name }) => ({ id, name }));

  return (
    <div className="flex flex-1 flex-col">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-zinc-200 px-4 py-3 dark:border-zinc-800">
        <div className="flex items-center gap-3">
          <Link href="/warehouses" className="flex items-center gap-2 font-semibold text-zinc-900 dark:text-zinc-100">
            <span aria-hidden className="h-4 w-4 rounded-sm bg-blue-600" />
            FlowForge
          </Link>
          <span className="rounded border border-dashed border-orange-300 bg-orange-50 px-1.5 py-0.5 text-xs text-orange-800 dark:border-orange-800 dark:bg-orange-950 dark:text-orange-300">
            Wireframe · mock data
          </span>
        </div>
        {ROLE_TOGGLE_ENABLED ? (
          <RoleToggle role={role} />
        ) : (
          <span className="text-xs text-zinc-500">Signed in as {role}</span>
        )}
      </header>
      <div className="flex flex-1 flex-col lg:flex-row">
        <aside className="border-b border-zinc-200 p-4 lg:w-56 lg:shrink-0 lg:border-r lg:border-b-0 dark:border-zinc-800">
          <PortalNav role={role} warehouses={warehouses} />
        </aside>
        <main className="min-w-0 flex-1 p-4 lg:p-6">{children}</main>
      </div>
    </div>
  );
}

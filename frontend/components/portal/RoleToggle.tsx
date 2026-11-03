"use client";

import { usePathname, useRouter } from "next/navigation";

import { setMockRole } from "@/lib/mockRoleActions";
import type { Role } from "@/types";

const ROLES: { role: Role; label: string }[] = [
  { role: "admin", label: "Admin" },
  { role: "supervisor", label: "Supervisor" },
];

// Dev-only switch between the two portal views (see lib/mockRole.ts).
export function RoleToggle({ role }: { role: Role }) {
  const router = useRouter();
  const pathname = usePathname();

  async function choose(next: Role) {
    await setMockRole(next);
    // A supervisor can't stay on a Setup page; everywhere else just re-render with the new role.
    if (next === "supervisor" && (pathname.startsWith("/admin") || pathname.startsWith("/concepts"))) router.push("/403");
    else router.refresh();
  }

  return (
    <div role="group" aria-label="Mock role (dev only)" className="flex items-center gap-2 text-xs">
      <span className="text-zinc-500">Mock role</span>
      <div className="flex rounded-md border border-zinc-300 p-0.5 dark:border-zinc-700">
        {ROLES.map(({ role: r, label }) => (
          <button
            key={r}
            type="button"
            aria-pressed={r === role}
            onClick={() => choose(r)}
            className={`rounded px-2.5 py-1 font-medium ${
              r === role
                ? "bg-blue-600 text-white dark:bg-blue-500"
                : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
            }`}
          >
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { Role } from "@/types";

interface NavItem {
  href: string;
  label: string;
}

// Side navigation shared by every portal page. Supervisors and admins see the same links, and admins also
// get the Setup section. There is one warehouse, so its name heads the list.
export function PortalNav({ role, warehouseName }: { role: Role; warehouseName: string }) {
  const pathname = usePathname();

  const site: NavItem[] = [
    { href: "/console", label: "Console" },
    { href: "/exceptions", label: "Exceptions" },
    { href: "/metrics", label: "Metrics" },
  ];
  const setup: NavItem[] = [
    { href: "/admin/layout", label: "Layout editor" },
    { href: "/admin/inventory", label: "SKUs & inventory" },
    { href: "/admin/workforce", label: "Workforce" },
    { href: "/admin/simulation", label: "Simulation" },
    { href: "/admin/users", label: "Users & roles" },
  ];

  // Future-state wireframes for Trent's areas. Admin-only, like Setup.
  const concepts: NavItem[] = [
    { href: "/concepts", label: "Overview" },
    { href: "/concepts/backend", label: "Backend console" },
    { href: "/concepts/workforce", label: "Workforce" },
  ];

  return (
    <nav aria-label="Portal" className="flex flex-col gap-5 text-sm">
      <NavSection title={warehouseName} items={site} pathname={pathname} />
      {role === "admin" && <NavSection title="Setup" items={setup} pathname={pathname} />}
      {role === "admin" && <NavSection title="Concepts (future)" items={concepts} pathname={pathname} />}
    </nav>
  );
}

function NavSection({ title, items, pathname }: { title?: string; items: NavItem[]; pathname: string }) {
  return (
    <div>
      {title && <p className="mb-1 px-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">{title}</p>}
      <ul className="flex flex-col gap-0.5">
        {items.map(({ href, label }) => {
          const active = pathname === href;
          return (
            <li key={href}>
              <Link
                href={href}
                aria-current={active ? "page" : undefined}
                className={`block rounded-md px-2 py-1.5 ${
                  active
                    ? "bg-blue-50 font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300"
                    : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-900"
                }`}
              >
                {label}
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

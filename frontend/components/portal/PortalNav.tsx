"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { Role } from "@/types";

interface NavItem {
  href: string;
  label: string;
}

// Side navigation shared by every portal page. Supervisors and admins see the same links, and admins also
// get the Setup section. Per-warehouse links follow whichever warehouse is open (warehouse 1 by default).
export function PortalNav({ role, warehouses }: { role: Role; warehouses: { id: number; name: string }[] }) {
  const pathname = usePathname();
  const match = pathname.match(/^\/(?:admin\/)?w\/(\d+)/);
  const current = warehouses.find((w) => w.id === Number(match?.[1])) ?? warehouses[0];

  const site: NavItem[] = [
    { href: `/w/${current.id}/console`, label: "Console" },
    { href: `/w/${current.id}/exceptions`, label: "Exceptions" },
    { href: `/w/${current.id}/metrics`, label: "Metrics" },
  ];
  const setup: NavItem[] = [
    { href: "/admin/warehouses/new", label: "New warehouse" },
    { href: `/admin/w/${current.id}/layout`, label: "Layout editor" },
    { href: `/admin/w/${current.id}/inventory`, label: "SKUs & inventory" },
    { href: `/admin/w/${current.id}/workforce`, label: "Workforce" },
    { href: `/admin/w/${current.id}/simulation`, label: "Simulation" },
    { href: "/admin/users", label: "Users & roles" },
  ];

  return (
    <nav aria-label="Portal" className="flex flex-col gap-5 text-sm">
      <NavSection items={[{ href: "/warehouses", label: "All warehouses" }]} pathname={pathname} />
      <NavSection title={current.name} items={site} pathname={pathname} />
      {role === "admin" && <NavSection title="Setup" items={setup} pathname={pathname} />}
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

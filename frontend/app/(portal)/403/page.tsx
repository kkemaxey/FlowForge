import Link from "next/link";

export default function NotAuthorizedPage() {
  return (
    <div className="flex flex-col items-start gap-3">
      <h1 className="text-xl font-semibold text-zinc-900 dark:text-zinc-100">Not authorized</h1>
      <p className="text-sm text-zinc-600 dark:text-zinc-400">
        This page is part of Setup, which only admins can use. Ask an admin if you need access.
      </p>
      <Link href="/warehouses" className="text-sm underline underline-offset-2">
        Back to warehouses
      </Link>
    </div>
  );
}

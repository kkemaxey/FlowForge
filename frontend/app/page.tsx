"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getHealth } from "@/lib/api-client";

export default function Home() {
  const [apiStatus, setApiStatus] = useState("checking…");

  useEffect(() => {
    getHealth()
      .then((body) => setApiStatus(body.status))
      .catch(() => setApiStatus("unreachable"));
  }, []);

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-semibold">FlowForge</h1>
      <p className="text-zinc-600 dark:text-zinc-400">API status: {apiStatus}</p>
      <Link href="/console" className="rounded-md bg-zinc-900 px-4 py-2 text-white dark:bg-zinc-100 dark:text-zinc-900">
        Open console
      </Link>
    </main>
  );
}

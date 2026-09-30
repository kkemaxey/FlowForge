"use client";

import { onAuthStateChanged } from "firebase/auth";
import { useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { getFirebaseAuth } from "@/lib/firebase";

// Auth gate: every page under /console requires a signed-in supervisor.
export default function ConsoleLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    return onAuthStateChanged(getFirebaseAuth(), (user) => {
      if (user) setReady(true);
      else router.replace("/login");
    });
  }, [router]);

  if (!ready) {
    return <p className="p-8 text-zinc-500">Checking sign-in…</p>;
  }
  return <div className="flex flex-1 flex-col">{children}</div>;
}

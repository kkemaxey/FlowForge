"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

import { apiFetch } from "@/lib/api-client";
import { MOCK_LOCATIONS, MOCK_TASKS, MOCK_WORKERS } from "@/mocks/consoleMocks";
import type { Worker, WorkerList } from "@/types";

import type { GridLocation, GridTask } from "./types";

// Must be a literal process.env reference so Next.js inlines it at build time.
export const USE_MOCKS = (process.env.NEXT_PUBLIC_USE_MOCKS ?? "true") === "true";

const POLL_MS = 2000;
const TASK_LIMIT = 500;
// Fetched one status at a time because GET /tasks sorts oldest first: without a status filter, 500
// picked tasks would push every new task off the list. Exceptions come first so the reassign dropdown
// lists stuck tasks at the top.
const UNFINISHED_STATUSES = ["exception", "assigned", "open"] as const;

interface ConsoleData {
  locations: GridLocation[];
  workers: Worker[];
  tasks: GridTask[]; // unfinished tasks only
  loading: boolean; // true until the first response or error
  error: string | null; // the last poll failed; the last good data stays on screen
  refresh: () => Promise<void>;
}

const ConsoleDataContext = createContext<ConsoleData | null>(null);

export function useConsoleData(): ConsoleData {
  const data = useContext(ConsoleDataContext);
  if (!data) throw new Error("useConsoleData must be used inside ConsoleDataProvider");
  return data;
}

async function fetchTasks(): Promise<GridTask[]> {
  const pages = await Promise.all(
    UNFINISHED_STATUSES.map((status) =>
      apiFetch<{ items: GridTask[] }>(`/api/v1/tasks?status=${status}&limit=${TASK_LIMIT}`),
    ),
  );
  return pages.flatMap((page) => page.items);
}

/** Polls workers and tasks once for the grid map and the controls, so they always agree. */
export function ConsoleDataProvider({ children }: { children: ReactNode }) {
  const [locations, setLocations] = useState<GridLocation[]>(USE_MOCKS ? MOCK_LOCATIONS : []);
  const [workers, setWorkers] = useState<Worker[]>(USE_MOCKS ? MOCK_WORKERS : []);
  const [tasks, setTasks] = useState<GridTask[]>(USE_MOCKS ? MOCK_TASKS : []);
  const [loading, setLoading] = useState(!USE_MOCKS);
  const [error, setError] = useState<string | null>(null);
  const latestRequest = useRef(0); // only the newest request may update state
  const locationsLoaded = useRef(false); // the warehouse layout doesn't change, so it loads once

  const refresh = useCallback(async () => {
    if (USE_MOCKS) return;
    const request = ++latestRequest.current;
    try {
      const [workerList, taskList, locationList] = await Promise.all([
        apiFetch<WorkerList>("/api/v1/workers?limit=500"),
        fetchTasks(),
        locationsLoaded.current ? null : apiFetch<{ items: GridLocation[] }>("/api/v1/locations"),
      ]);
      if (locationList) {
        locationsLoaded.current = true;
        setLocations(locationList.items);
      }
      // A slower, older response must not overwrite a newer one, such as the refresh after a reassign.
      if (request !== latestRequest.current) return;
      setWorkers(workerList.items);
      setTasks(taskList);
      setError(null);
    } catch {
      if (request === latestRequest.current) setError("Could not reach the backend. Showing the last good data.");
    } finally {
      if (request === latestRequest.current) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (USE_MOCKS) return;
    let inFlight = false;
    async function poll() {
      // Skip a tick rather than stacking requests when the backend is slow.
      if (inFlight) return;
      inFlight = true;
      await refresh();
      inFlight = false;
    }
    void poll();
    const id = setInterval(poll, POLL_MS);
    return () => {
      clearInterval(id);
      latestRequest.current += 1; // ignore responses that arrive after unmount
    };
  }, [refresh]);

  const value = useMemo(
    () => ({ locations, workers, tasks, loading, error, refresh }),
    [locations, workers, tasks, loading, error, refresh],
  );
  return <ConsoleDataContext.Provider value={value}>{children}</ConsoleDataContext.Provider>;
}

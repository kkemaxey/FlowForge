import { useEffect, useState } from "react";

import { getMetrics, getOrders, getTasks, type LiveMetrics, type Order, type Task } from "./data";

export interface LiveBoardData {
  orders: Order[];
  tasks: Task[];
  metrics: LiveMetrics;
  updatedAt: Date;
}

/**
 * Polls orders, tasks and metrics together every `intervalMs` (2 seconds by default).
 *
 * - `loading` is true only until the first response (or first error) comes back.
 * - If a later poll fails, the last good data stays on screen and `error` explains what went wrong.
 * - The interval is cleared when the board unmounts, and late responses are ignored after that.
 */
export function useLiveBoard(intervalMs = 2000) {
  const [data, setData] = useState<LiveBoardData | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false; // set on unmount so we never update state for a component that's gone
    let inFlight = false; // true while a poll is waiting on the backend

    async function poll() {
      // Skip a tick rather than stacking requests when the backend is slow.
      if (inFlight) return;
      inFlight = true;
      try {
        // Fetch all three at once so the orders, tasks and metrics on screen come from the same moment.
        const [orders, tasks, metrics] = await Promise.all([getOrders(), getTasks(), getMetrics()]);
        if (!cancelled) {
          setData({ orders, tasks, metrics, updatedAt: new Date() });
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err : new Error(String(err)));
      } finally {
        inFlight = false;
      }
    }

    // Load right away, then keep polling on the interval.
    poll();
    const id = setInterval(poll, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [intervalMs]);

  return { data, error, loading: data === null && error === null };
}

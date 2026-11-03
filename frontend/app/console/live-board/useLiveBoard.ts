import { useEffect, useState } from "react";

import { getMetrics, getOrders, getTasks, type LiveMetrics, type Order, type Task } from "./data";

export interface LiveBoardData {
  orders: Order[];
  tasks: Task[];
  metrics: LiveMetrics | null; // null while the metrics endpoint is missing or failing
  updatedAt: Date;
}

/**
 * Polls orders, tasks and metrics together every `intervalMs` (2 seconds by default).
 *
 * - Orders and tasks are required; metrics are optional. If only metrics fail, the board still updates
 *   and the throughput tile shows a dash.
 * - `loading` is true only until the first response (or first error) comes back.
 * - If orders or tasks fail on a later poll, the last good data stays on screen and `error` explains why.
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
        // Fetch all three at once so the numbers on screen come from the same moment. allSettled (not all)
        // so a failing metrics call can't hide orders and tasks that loaded fine.
        const [orders, tasks, metrics] = await Promise.allSettled([getOrders(), getTasks(), getMetrics()]);
        if (cancelled) return;
        if (orders.status === "fulfilled" && tasks.status === "fulfilled") {
          setData({
            orders: orders.value,
            tasks: tasks.value,
            metrics: metrics.status === "fulfilled" ? metrics.value : null,
            updatedAt: new Date(),
          });
          setError(null);
        } else {
          const reason = orders.status === "rejected" ? orders.reason : (tasks as PromiseRejectedResult).reason;
          setError(reason instanceof Error ? reason : new Error(String(reason)));
        }
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

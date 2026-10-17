"use client";

import { useEffect, useState } from "react";

import { getMetrics, getOrders, getTasks, type LiveMetrics, type Order, type Task } from "./data";

export interface LiveBoardData {
  orders: Order[];
  tasks: Task[];
  metrics: LiveMetrics;
  updatedAt: Date;
}

/** Polls orders, tasks and metrics together. Keeps the last good data if a poll fails. */
export function useLiveBoard(intervalMs = 2000) {
  const [data, setData] = useState<LiveBoardData | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    let cancelled = false;
    let inFlight = false;

    async function poll() {
      // Skip a tick rather than stacking requests when the backend is slow.
      if (inFlight) return;
      inFlight = true;
      try {
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

    poll();
    const id = setInterval(poll, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [intervalMs]);

  return { data, error, loading: data === null && error === null };
}

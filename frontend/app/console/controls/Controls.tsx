"use client";

import { useCallback, useEffect, useState } from "react";

import { Card } from "@/components/ui/Card";
import { apiFetch } from "@/lib/api-client";
import { MOCK_TASKS, MOCK_WORKERS } from "@/mocks/consoleMocks";

import type { GridTask, GridWorker } from "../types";

const USE_MOCKS = (process.env.NEXT_PUBLIC_USE_MOCKS ?? "true") === "true";

interface GeneratorStatus {
  running: boolean;
  created: number;
  rejected: number;
}

// apiFetch is being changed to expose the backend's {detail, code}; read it from whichever shape it throws.
function errorCode(err: unknown): string | undefined {
  const e = err as { code?: unknown; body?: { code?: unknown } } | null;
  const code = e?.code ?? e?.body?.code;
  return typeof code === "string" ? code : undefined;
}

const btn =
  "rounded-md border border-zinc-300 px-2 py-1 text-xs font-medium hover:bg-zinc-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-zinc-700 dark:hover:bg-zinc-800";
const field =
  "rounded-md border border-zinc-300 bg-white px-2 py-1 text-sm dark:border-zinc-700 dark:bg-zinc-900";

export function Controls() {
  const [tasks, setTasks] = useState<GridTask[]>([]);
  const [workers, setWorkers] = useState<GridWorker[]>([]);
  const [taskId, setTaskId] = useState("");
  const [workerId, setWorkerId] = useState("");
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [completeOrders, setCompleteOrders] = useState<Set<number>>(new Set());
  const [orderMessage, setOrderMessage] = useState<string | null>(null);
  const [generator, setGenerator] = useState<GeneratorStatus | null>(null);
  const [generatorMessage, setGeneratorMessage] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (USE_MOCKS) {
      setTasks(MOCK_TASKS);
      setWorkers(MOCK_WORKERS);
      return;
    }
    const [t, w] = await Promise.all([
      apiFetch<{ items: GridTask[] }>("/api/v1/tasks?limit=500"),
      apiFetch<GridWorker[]>("/api/v1/workers"),
    ]);
    setTasks(t.items);
    setWorkers(w);
  }, []);

  const refreshGenerator = useCallback(async () => {
    if (USE_MOCKS) return;
    setGenerator(await apiFetch<GeneratorStatus>("/api/v1/generator"));
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        if (USE_MOCKS) {
          setTasks(MOCK_TASKS);
          setWorkers(MOCK_WORKERS);
          return;
        }
        const [t, w, g] = await Promise.all([
          apiFetch<{ items: GridTask[] }>("/api/v1/tasks?limit=500"),
          apiFetch<GridWorker[]>("/api/v1/workers"),
          apiFetch<GeneratorStatus>("/api/v1/generator"),
        ]);
        if (cancelled) return;
        setTasks(t.items);
        setWorkers(w);
        setGenerator(g);
      } catch {
        if (!cancelled) setMessage("Could not load tasks and workers.");
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const reassignable = tasks.filter((t) => t.status !== "picked");
  const idleWorkers = workers.filter((w) => w.status === "idle" && w.is_active);
  const orderIds = [...new Set(tasks.map((t) => t.order_id))].sort((a, b) => a - b);
  const selected = tasks.find((t) => String(t.task_id) === taskId);

  async function reassign() {
    if (!selected || !workerId) return;
    setBusy(true);
    setMessage(null);
    try {
      if (USE_MOCKS) {
        setMessage(`Mock: task ${selected.task_id} would go to worker ${workerId}.`);
      } else {
        await apiFetch(`/api/v1/tasks/${selected.task_id}/reassign`, {
          method: "POST",
          body: JSON.stringify({
            worker_id: Number(workerId),
            expected_version: selected.version,
            ...(reason.trim() && { reason: reason.trim() }),
          }),
        });
        setMessage(`Task ${selected.task_id} reassigned.`);
        setReason("");
        setWorkerId("");
        await refresh();
      }
    } catch (err) {
      const code = errorCode(err);
      if (code === "version_conflict") setMessage("This task changed while you were looking at it. Refreshed; try again.");
      else if (code === "worker_unavailable") setMessage("That worker isn't idle anymore. Pick another worker.");
      else if (code === "invalid_transition") setMessage("This task has already been picked. Refreshed.");
      else if (code === "assignment_conflict") setMessage("Another change happened at the same time. Refreshed; try again.");
      else setMessage("Reassign failed.");
      if (code) await refresh().catch(() => {});
    } finally {
      setBusy(false);
    }
  }

  async function expedite(orderId: number) {
    setOrderMessage(null);
    try {
      if (USE_MOCKS) {
        setOrderMessage(`Mock: order ${orderId} moved to front of queue.`);
        return;
      }
      await apiFetch(`/api/v1/orders/${orderId}/expedite`, { method: "POST" });
      setOrderMessage(`Order ${orderId} moved to front of queue.`);
      await refresh();
    } catch (err) {
      const code = errorCode(err);
      if (code === "order_complete") {
        setCompleteOrders((prev) => new Set(prev).add(orderId));
        setOrderMessage(`Order ${orderId} is already complete.`);
      } else if (code === "version_conflict") {
        setOrderMessage(`Order ${orderId} changed at the same time. Try again.`);
      } else {
        setOrderMessage("Expedite failed.");
      }
    }
  }

  async function generatorAction(action: "start" | "stop") {
    setGeneratorMessage(null);
    try {
      if (USE_MOCKS) {
        setGeneratorMessage(`Mock: generator ${action}.`);
        return;
      }
      await apiFetch(`/api/v1/generator/${action}`, {
        method: "POST",
        ...(action === "start" && { body: JSON.stringify({ order_rate: 30, seed: 480 }) }),
      });
      await refreshGenerator();
    } catch {
      setGeneratorMessage(`Could not ${action} the generator.`);
    }
  }

  return (
    <Card title="Reassign and expedite">
      <div className="flex flex-col gap-4 text-sm">
        <section aria-label="Reassign a task" className="flex flex-col gap-2">
          <h3 className="font-medium">Reassign task</h3>
          <label className="flex flex-col gap-1">
            Task
            <select className={field} value={taskId} onChange={(e) => setTaskId(e.target.value)}>
              <option value="">Select a task…</option>
              {reassignable.map((t) => (
                <option key={t.task_id} value={t.task_id}>
                  Task {t.task_id} · order {t.order_id} · {t.status}
                  {t.current_assignment ? ` · worker ${t.current_assignment.worker_id}` : ""}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            Worker (idle only)
            <select className={field} value={workerId} onChange={(e) => setWorkerId(e.target.value)}>
              <option value="">Select a worker…</option>
              {idleWorkers.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name} ({w.kind})
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            Reason (optional)
            <input className={field} value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <div className="flex gap-2">
            <button className={btn} disabled={!selected || !workerId || busy} onClick={reassign}>
              Reassign
            </button>
            <button className={btn} disabled={busy} onClick={() => refresh().catch(() => setMessage("Refresh failed."))}>
              Refresh
            </button>
          </div>
          {message && <p role="status">{message}</p>}
        </section>

        <section aria-label="Expedite orders" className="flex flex-col gap-2">
          <h3 className="font-medium">Expedite (move to front of queue)</h3>
          {orderIds.length === 0 && <p className="text-zinc-500">No orders with tasks.</p>}
          <ul className="flex flex-wrap gap-2">
            {orderIds.map((id) => (
              <li key={id}>
                <button className={btn} disabled={completeOrders.has(id)} onClick={() => expedite(id)}>
                  Order {id}: Expedite{completeOrders.has(id) ? " (complete)" : ""}
                </button>
              </li>
            ))}
          </ul>
          {orderMessage && <p role="status">{orderMessage}</p>}
        </section>

        <section aria-label="Order generator" className="flex flex-col gap-2">
          <h3 className="font-medium">Order generator</h3>
          <p className="text-zinc-600 dark:text-zinc-400">
            {generator ? (generator.running ? `Running · ${generator.created} created` : "Stopped") : "Status unknown"}
          </p>
          <div className="flex gap-2">
            <button className={btn} disabled={generator?.running} onClick={() => generatorAction("start")}>
              Start
            </button>
            <button className={btn} disabled={generator !== null && !generator.running} onClick={() => generatorAction("stop")}>
              Stop
            </button>
          </div>
          {generatorMessage && <p role="status">{generatorMessage}</p>}
        </section>
      </div>
    </Card>
  );
}

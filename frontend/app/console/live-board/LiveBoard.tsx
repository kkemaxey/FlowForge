"use client";

import Link from "next/link";

import { Card } from "@/components/ui/Card";

import {
  USE_MOCKS,
  type ExceptionType,
  type LiveMetrics,
  type LiveTaskStatus,
  type Order,
  type OrderStatus,
  type Task,
} from "./data";
import { collectExceptions, sortNewestFirst } from "./boardLogic";
import { KpiStrip } from "./KpiStrip";
import { useLiveBoard } from "./useLiveBoard";

// Owner: Jayden
//
// The live board panel on the supervisor console (Sprint 1 + 2). Top to bottom it shows:
//   1. a status line (last update time, whether we're on mock data, refresh errors)
//   2. a red exception banner when a task is stuck (e.g. stockout)
//   3. the KPI strip: throughput, WIP and on-time %
//   4. task counts per status
//   5. the orders table, newest first, with late orders highlighted
// Data comes from useLiveBoard(), which polls every 2 seconds. This is a Client Component ("use client")
// because polling needs browser state and timers.

// Badge colors per order status.
const ORDER_BADGE: Record<OrderStatus, string> = {
  new: "bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300",
  in_progress: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  complete: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  late: "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300",
};

// The order and colors of the task-count boxes.
const TASK_STATUSES: { status: LiveTaskStatus; label: string; className: string }[] = [
  { status: "open", label: "Open", className: "text-zinc-700 dark:text-zinc-300" },
  { status: "assigned", label: "Assigned", className: "text-blue-700 dark:text-blue-400" },
  { status: "picked", label: "Picked", className: "text-amber-700 dark:text-amber-400" },
  { status: "complete", label: "Complete", className: "text-emerald-700 dark:text-emerald-400" },
  { status: "exception", label: "Exception", className: "text-red-700 dark:text-red-400" },
];

const EXCEPTION_LABEL: Record<ExceptionType, string> = {
  stockout: "Stockout",
  worker_down: "Worker down",
};

const formatTime = (value: string | Date) =>
  new Date(value).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" });

// warehouseId scopes the board to one site; leave it out to show everything.
export function LiveBoard({ warehouseId }: { warehouseId?: number }) {
  const { data, error, loading } = useLiveBoard(2000, warehouseId);

  return (
    <Card title="Live board">
      <div className="flex flex-col gap-4">
        <StatusLine updatedAt={data?.updatedAt} error={error} />
        {loading && <p className="text-sm text-zinc-500">Loading orders and tasks…</p>}
        {!data && error && <p className="text-sm text-red-600 dark:text-red-400">Couldn&apos;t load the live board.</p>}
        {data && (
          <>
            <ExceptionBanner tasks={data.tasks} metrics={data.metrics} />
            <KpiStrip metrics={data.metrics} orders={data.orders} />
            <TaskSummary counts={data.metrics.task_counts} />
            <OrdersTable orders={data.orders} warehouseId={warehouseId} />
          </>
        )}
      </div>
    </Card>
  );
}

// Small header line: green/red dot, last update time, mock-data tag, and refresh errors.
function StatusLine({ updatedAt, error }: { updatedAt?: Date; error: Error | null }) {
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-500">
      <span className={`h-2 w-2 rounded-full ${error ? "bg-red-500" : "bg-emerald-500"}`} aria-hidden />
      <span>{updatedAt ? `Updated ${formatTime(updatedAt)}` : "Connecting…"}</span>
      {USE_MOCKS && (
        <span className="rounded bg-zinc-100 px-1.5 py-0.5 font-medium dark:bg-zinc-800">Mock data</span>
      )}
      {error && updatedAt && <span className="text-red-600 dark:text-red-400">Refresh failed: {error.message}</span>}
    </div>
  );
}

// Red alert listing every task in exception. The grid map (Aalan) handles showing it on the map;
// this only flags it on the live board.
function ExceptionBanner({ tasks, metrics }: { tasks: Task[]; metrics: LiveMetrics }) {
  const alerts = collectExceptions(tasks, metrics);
  if (alerts.length === 0) return null;

  return (
    <div
      role="alert"
      className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/60 dark:text-red-200"
    >
      <p className="font-semibold">
        {alerts.length === 1 ? "Exception on the floor" : `${alerts.length} exceptions on the floor`}
      </p>
      <ul className="mt-1 space-y-0.5">
        {alerts.map((a) => (
          <li key={a.taskId}>
            {EXCEPTION_LABEL[a.type]} · Task #{a.taskId} (order #{a.orderId}) at <span className="font-mono">{a.location}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// How many tasks are in each status right now, from the metrics endpoint.
function TaskSummary({ counts }: { counts: Record<LiveTaskStatus, number> }) {
  return (
    <div>
      <h3 className="mb-1.5 text-xs font-medium text-zinc-500">Tasks by status</h3>
      <div className="grid grid-cols-5 gap-2 text-center">
        {TASK_STATUSES.map(({ status, label, className }) => (
          <div key={status} className="rounded-md bg-zinc-50 px-1 py-2 dark:bg-zinc-900">
            <p className={`text-lg font-semibold tabular-nums ${className}`}>{counts[status] ?? 0}</p>
            <p className="text-[11px] text-zinc-500">{label}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// Orders table, newest first. Late orders get a red row and red due time. Inside a warehouse, each order
// number links to its detail page.
function OrdersTable({ orders, warehouseId }: { orders: Order[]; warehouseId?: number }) {
  const sorted = sortNewestFirst(orders);

  return (
    <div>
      <h3 className="mb-1.5 text-xs font-medium text-zinc-500">Orders</h3>
      {sorted.length === 0 ? (
        <p className="text-sm text-zinc-500">No orders yet.</p>
      ) : (
        <div className="max-h-80 overflow-auto rounded-md border border-zinc-200 dark:border-zinc-800">
          <table className="w-full text-left text-sm">
            <thead className="sticky top-0 bg-zinc-50 text-xs text-zinc-500 dark:bg-zinc-900">
              <tr>
                <th className="px-3 py-2 font-medium">Order</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 text-right font-medium">Lines</th>
                <th className="px-3 py-2 font-medium">Created</th>
                <th className="px-3 py-2 font-medium">Due</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
              {sorted.map((order) => {
                const late = order.status === "late";
                return (
                  <tr key={order.id} className={late ? "bg-red-50 dark:bg-red-950/40" : undefined}>
                    <td className="px-3 py-2 font-mono text-zinc-900 dark:text-zinc-100">
                      {warehouseId === undefined ? (
                        `#${order.id}`
                      ) : (
                        <Link href={`/w/${warehouseId}/orders/${order.id}`} className="underline underline-offset-2">
                          #{order.id}
                        </Link>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${ORDER_BADGE[order.status]}`}>
                        {order.status.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">{order.lines.length}</td>
                    <td className="px-3 py-2 tabular-nums text-zinc-600 dark:text-zinc-400">{formatTime(order.created_at)}</td>
                    <td
                      className={`px-3 py-2 tabular-nums ${late ? "font-medium text-red-700 dark:text-red-400" : "text-zinc-600 dark:text-zinc-400"}`}
                    >
                      {formatTime(order.due_at)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

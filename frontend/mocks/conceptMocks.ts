import { DEMO_WORKERS } from "./demoWarehouse";

// Data for the /concepts pages, scoped to Trent's areas: workforce, deploy, CI and tests, and where those
// touch other modules (route gates, the events log). Facts about main come from the code at 25605ca; facts
// about feature/simulation from that branch. Statuses, timestamps and history entries are mock.

// ---------------------------------------------------------------- Open steps --------------------------------

export type StepState = "ready" | "blocked" | "decision" | "later";

export interface OpenStep {
  id: string;
  title: string;
  detail: string;
  state: StepState;
  waitingOn?: string;
  anchor: string;
  source: string;
}

export const OPEN_STEPS: OpenStep[] = [
  {
    id: "gates",
    title: "Gate the workforce routes",
    detail: "Reads need a signed-in user, writes need require_supervisor (on main since 0.9.0). No workforce route uses either yet.",
    state: "ready",
    anchor: "gates",
    source: "Design doc conventions; walkthrough “Not in this branch”",
  },
  {
    id: "exc-tests",
    title: "Exception-flow tests",
    detail: "Six test files live on feature/simulation. They land once it rebases onto main and uses main's Worker and Event models.",
    state: "blocked",
    waitingOn: "Kendyn: rebase feature/simulation",
    anchor: "tests",
    source: "SPRINT_PLAN Sprint 2",
  },
  {
    id: "test-gaps",
    title: "Fill test gaps and cover growth work",
    detail: "State machine, assigner and reassign suites exist (Kanayo). Add auth-gate tests for workforce and cover whichever growth goals the team picks.",
    state: "ready",
    anchor: "tests",
    source: "SPRINT_PLAN Sprints 1, 3, 4",
  },
  {
    id: "deploy",
    title: "Deploy API and frontend",
    detail: "Nothing is deployed. The Dockerfile targets Cloud Run, but Cloud SQL is retired, so the production database has no home yet.",
    state: "decision",
    waitingOn: "Team: where production MySQL runs",
    anchor: "deploy",
    source: "SPRINT_PLAN Sprints 0, 3",
  },
  {
    id: "events",
    title: "Events → metrics",
    detail: "Main and feature/simulation disagree on the events table's column names, and the branch's allowlist would reject six types main already writes.",
    state: "blocked",
    waitingOn: "Kendyn: align the Event model and allowlist",
    anchor: "events",
    source: "Stack outline role; walkthrough follow-ups",
  },
  {
    id: "questions",
    title: "Workforce questions for Kanayo",
    detail: "Grid upper bound, whether the assigner bumps workers.version and uses list_idle_workers(), and MySQL 8.0 → 8.4.",
    state: "decision",
    waitingOn: "Kanayo",
    anchor: "decisions",
    source: "Walkthrough open questions",
  },
  {
    id: "freeze",
    title: "Freeze prep",
    detail: "Verify the production deploy (env vars, migrations, auth domains), demo seed data, README and setup docs.",
    state: "later",
    waitingOn: "Sprint 5 (Nov 19)",
    anchor: "deploy",
    source: "SPRINT_PLAN Sprint 5",
  },
];

// ---------------------------------------------------------------- Route gates -------------------------------

export type Gate = "public" | "signed in" | "supervisor";

export interface Route {
  method: "GET" | "POST" | "PATCH" | "DELETE";
  path: string;
  owner: string;
  mine: boolean;
  needs: Gate; // what the design doc's conventions require
  today: "none" | "token"; // what main enforces at 25605ca
}

const route = (method: Route["method"], path: string, owner: string, today: Route["today"] = "none"): Route => ({
  method,
  path,
  owner,
  mine: owner === "Trent",
  needs: path === "/health" ? "public" : path.startsWith("/auth") || method === "GET" ? "signed in" : "supervisor",
  today,
});

export const ROUTES: Route[] = [
  route("GET", "/api/v1/workers", "Trent"),
  route("GET", "/api/v1/workers/{id}", "Trent"),
  route("POST", "/api/v1/workers", "Trent"),
  route("PATCH", "/api/v1/workers/{id}", "Trent"),
  route("DELETE", "/api/v1/workers/{id}", "Trent"),
  route("GET", "/health", "Shared"),
  route("POST", "/auth/session", "Brock", "token"),
  route("GET", "/auth/me", "Brock", "token"),
  route("POST", "/api/v1/orders", "Kanayo"),
  route("GET", "/api/v1/orders/{id}", "Kanayo"),
  route("POST", "/api/v1/orders/{id}/expedite", "Kanayo"),
  route("GET", "/api/v1/tasks", "Kanayo"),
  route("POST", "/api/v1/tasks/{id}/reassign", "Kanayo"),
  route("POST", "/api/v1/assignments/run", "Kanayo"),
  route("GET", "/api/v1/generator", "Kanayo"),
  route("POST", "/api/v1/generator/start", "Kanayo"),
  route("POST", "/api/v1/generator/stop", "Kanayo"),
];

// ---------------------------------------------------------------- Tests and CI ------------------------------

export interface Suite {
  file: string;
  area: string;
  author: string;
  tests: number | null; // test functions on main (parametrised cases count once)
  state: "on main" | "on a branch" | "to write";
  note?: string;
}

export const SUITES: Suite[] = [
  { file: "test_workforce_api.py", area: "Workforce routes", author: "Trent", tests: 29, state: "on main" },
  { file: "test_workforce_service.py", area: "Workforce service", author: "Trent", tests: 1, state: "on main" },
  { file: "test_request_logging.py", area: "Request ids", author: "Trent", tests: 3, state: "on main" },
  { file: "test_workforce_auth.py", area: "401 / 403 on workforce routes", author: "Trent", tests: null, state: "to write", note: "Goes with the route-gate change" },
  { file: "test_tasks.py", area: "Task state machine", author: "Kanayo", tests: 13, state: "on main" },
  { file: "test_assignment.py", area: "Greedy assigner", author: "Kanayo", tests: 23, state: "on main" },
  { file: "test_reassign.py", area: "Reassign", author: "Kanayo", tests: 14, state: "on main" },
  { file: "test_orders.py", area: "Order intake", author: "Kanayo", tests: 14, state: "on main" },
  { file: "test_expedite.py", area: "Expedite", author: "Kanayo", tests: 6, state: "on main" },
  { file: "test_generator.py", area: "Order generator", author: "Kanayo", tests: 20, state: "on main" },
  { file: "test_errors.py", area: "Error format", author: "Kanayo", tests: 4, state: "on main" },
  { file: "test_health.py", area: "/health", author: "Kanayo", tests: 1, state: "on main" },
  { file: "test_auth.py", area: "Auth session and me", author: "Brock", tests: 3, state: "on main" },
  { file: "test_exceptions_api.py", area: "Exception flow", author: "Kendyn", tests: null, state: "on a branch", note: "feature/simulation" },
  { file: "test_exceptions_list.py", area: "Open exceptions list", author: "Kendyn", tests: null, state: "on a branch", note: "feature/simulation" },
  { file: "test_simulator.py", area: "Simulator", author: "Kendyn", tests: null, state: "on a branch", note: "feature/simulation" },
  { file: "test_pick_api.py", area: "Pick", author: "Kendyn", tests: null, state: "on a branch", note: "feature/simulation" },
  { file: "test_throughput_api.py", area: "Throughput metric", author: "Kendyn", tests: null, state: "on a branch", note: "feature/simulation" },
  { file: "test_events_service.py", area: "Event recording", author: "Kendyn", tests: null, state: "on a branch", note: "feature/simulation" },
];

export const CI_JOBS = [
  { name: "backend", does: "pytest against a throwaway MySQL 8.0 with a random per-run password", gap: "Exception-flow suites not in yet; 8.0 vs 8.4 open" },
  { name: "docker", does: "docker build of backend/Dockerfile (python:3.12-slim, uvicorn on $PORT)", gap: "Builds the image, but nothing deploys it" },
  { name: "frontend", does: "npm ci, lint, build", gap: "No frontend tests; workforceLogic.ts is plain functions and easy to cover" },
];

// ---------------------------------------------------------------- Deploy ------------------------------------

export interface Env {
  name: string;
  where: string;
  state: "running" | "not deployed" | "undecided";
  detail: string;
}

export const ENVS: Env[] = [
  { name: "Local stack", where: "docker compose", state: "running", detail: "mysql:8.0 + backend on :8080, assigner loop on, alembic head 0003, python -m app.seed" },
  { name: "API", where: "Cloud Run", state: "not deployed", detail: "Image builds in CI; needs a service, secrets and a DATABASE_URL it can reach" },
  { name: "Frontend", where: "Vercel", state: "not deployed", detail: "Needs NEXT_PUBLIC_API_URL, NEXT_PUBLIC_USE_MOCKS=false and the Firebase web config" },
  { name: "Production MySQL", where: "?", state: "undecided", detail: "Cloud SQL is retired; local MySQL in Docker can't serve Cloud Run" },
];

export const DEPLOY_CHECKLIST = [
  { sprint: "0", text: "Backend Dockerfile", done: true },
  { sprint: "0", text: "CI on every PR (backend, docker, frontend jobs)", done: true },
  { sprint: "0", text: "Deploy the skeleton to Cloud Run and Vercel", done: false },
  { sprint: "3", text: "Check Cloud Run cold starts", done: false },
  { sprint: "3", text: "Check DB connection pooling under the assigner loop", done: false },
  { sprint: "5", text: "Env vars: DATABASE_URL, CORS_ORIGINS, FIREBASE_CREDENTIALS, ASSIGNER_*", done: false },
  { sprint: "5", text: "Migrations at head on production", done: false },
  { sprint: "5", text: "Firebase authorised domains include the Vercel URL", done: false },
  { sprint: "5", text: "Realistic demo seed data", done: false },
  { sprint: "5", text: "README and setup docs", done: false },
];

// ---------------------------------------------------------------- Events ------------------------------------

export const EVENT_TYPES = [
  { type: "worker_created", writer: "Trent · workforce", onMain: true, inAllowlist: false },
  { type: "worker_updated", writer: "Trent · workforce", onMain: true, inAllowlist: false },
  { type: "worker_deactivated", writer: "Trent · workforce", onMain: true, inAllowlist: false },
  { type: "order_received", writer: "Kanayo · orders", onMain: true, inAllowlist: true },
  { type: "task_created", writer: "Kanayo · orders", onMain: true, inAllowlist: true },
  { type: "task_assigned", writer: "Kanayo · assignment", onMain: true, inAllowlist: true },
  { type: "task_reassigned", writer: "Kanayo · tasks", onMain: true, inAllowlist: false },
  { type: "order_expedited", writer: "Kanayo · orders", onMain: true, inAllowlist: false },
  { type: "user_login", writer: "Brock · auth", onMain: true, inAllowlist: false },
  { type: "task_picked", writer: "Kendyn · simulation", onMain: false, inAllowlist: true },
  { type: "exception_opened", writer: "Kendyn · simulation", onMain: false, inAllowlist: true },
  { type: "worker_status_changed", writer: "Kendyn · simulation", onMain: false, inAllowlist: true },
];

export const EVENT_COLUMNS = [
  { main: "event_type  varchar(48)", branch: "type  varchar(32)", clash: true },
  { main: "occurred_at  datetime(3)", branch: "created_at  datetime(3)", clash: true },
  { main: "run_id  int, no FK", branch: "run_id  FK → sim_runs.id", clash: true },
  { main: "index (event_type, occurred_at)", branch: "index (run_id, type, created_at)", clash: true },
  { main: "order_id, task_id, worker_id, assignment_id, payload", branch: "same", clash: false },
];

// ---------------------------------------------------------------- Decisions ---------------------------------

export interface Decision {
  id: string;
  question: string;
  who: string;
  options: string[];
  lean: string;
  blocks: string;
}

export const DECISIONS: Decision[] = [
  {
    id: "prod-db",
    question: "Where does production MySQL run?",
    who: "Team",
    options: ["Cloud SQL for production only", "MySQL on a small VM next to Cloud Run", "Demo from the local Docker stack and skip the cloud deploy"],
    lean: "Cloud SQL for production only: the Dockerfile and sprint checklists already assume Cloud Run",
    blocks: "Deploy, freeze prep",
  },
  {
    id: "grid",
    question: "Upper bound for worker positions?",
    who: "Kanayo",
    options: ["WAREHOUSE_WIDTH / WAREHOUSE_HEIGHT in core/config.py (10 × 10) + 422 position_off_grid", "Read the size from a warehouses row, once one exists", "Keep non-negative only"],
    lean: "Config values now, swap for the warehouse's own size later (the plan is already in workforce/service.py)",
    blocks: "Position picker on the workforce page",
  },
  {
    id: "version",
    question: "Should the assigner bump workers.version on idle ↔ busy?",
    who: "Kanayo",
    options: ["Yes, and call list_idle_workers()", "No; PATCH and DELETE keep locking the row first"],
    lean: "Yes: a stale edit form then gets a clean 409 instead of relying on the row lock",
    blocks: "Nothing; the row lock covers it today",
  },
  {
    id: "mysql",
    question: "MySQL 8.0 (end of life April 2026) → 8.4 in Compose and CI?",
    who: "Kanayo",
    options: ["Move both to 8.4", "Stay on 8.0 to match production"],
    lean: "Decide together with the production database so all three match",
    blocks: "CI image, docker-compose.yml",
  },
  {
    id: "naming",
    question: "Update the DB doc to match the code?",
    who: "Kanayo",
    options: ["kind human (doc: picker), default status idle (doc: offline)", "speed float, x/y int (doc: decimal(4,2), smallint)"],
    lean: "Change the doc; every endpoint and test already uses the code's names",
    blocks: "Nothing; docs only",
  },
  {
    id: "metrics",
    question: "Who owns events → metrics wiring?",
    who: "Kendyn",
    options: ["Kendyn the endpoint and allowlist, Trent the cross-module tests", "Trent wires it end to end"],
    lean: "Kendyn the endpoint and allowlist, Trent the cross-module tests",
    blocks: "Events → metrics",
  },
];

// ---------------------------------------------------------------- Workforce ---------------------------------

export interface WorkerEvent {
  at: string;
  type: "worker_created" | "worker_updated" | "worker_deactivated" | "task_assigned" | "task_reassigned";
  text: string;
  by: string;
}

export interface ConceptWorker {
  id: number;
  name: string;
  kind: "human" | "robot";
  status: "idle" | "busy" | "down" | "offline";
  x: number;
  y: number;
  speed: number;
  is_active: boolean;
  version: number;
  openAssignment: number | null;
  events: WorkerEvent[];
}

const STATE: Record<number, Partial<ConceptWorker>> = {
  1: { status: "busy", openAssignment: 5531, version: 2, x: 0, y: 6, speed: 1.2 },
  2: { status: "busy", openAssignment: 5536 },
  3: { status: "busy", openAssignment: 5540, version: 1, x: 6, y: 3 },
  4: { status: "idle" },
  5: { status: "down", version: 1, x: 3, y: 4 },
  6: { status: "busy", openAssignment: 5538, speed: 2.5 },
  7: { status: "idle", speed: 2.5 },
  8: { status: "busy", openAssignment: 5541, speed: 2.5 },
  9: { status: "offline", is_active: false, version: 2, speed: 2.5 },
  10: { status: "idle", speed: 2.5 },
};

function history(id: number, name: string, s: Partial<ConceptWorker>): WorkerEvent[] {
  const events: WorkerEvent[] = [{ at: "Nov 3 09:12:04", type: "worker_created", text: `Created ${name}`, by: "seed" }];
  if (id === 1)
    events.push(
      { at: "Nov 3 13:40:11", type: "worker_updated", text: "y 0 → 6", by: "t.gaylord" },
      { at: "Nov 3 14:01:55", type: "worker_updated", text: "speed 1.0 → 1.2", by: "k.maxey" },
    );
  if (id === 3) events.push({ at: "Nov 3 14:03:42", type: "task_reassigned", text: "Task 322 from Morgan (auto)", by: "assigner" });
  if (id === 5) events.push({ at: "Nov 3 13:58:20", type: "worker_updated", text: "name Morgn → Morgan", by: "t.gaylord" });
  if (id === 9)
    events.push(
      { at: "Nov 3 12:30:00", type: "worker_updated", text: "speed 2.0 → 2.5", by: "t.gaylord" },
      { at: "Nov 3 13:15:47", type: "worker_deactivated", text: "Deactivated", by: "t.gaylord" },
    );
  if (s.openAssignment) events.push({ at: "Nov 3 14:04:51", type: "task_assigned", text: `Assignment ${s.openAssignment} opened`, by: "greedy_v1" });
  return events.reverse();
}

export const CONCEPT_WORKERS: ConceptWorker[] = DEMO_WORKERS.map((w) => {
  const s = STATE[w.id];
  return {
    id: w.id,
    name: w.name,
    kind: w.kind,
    x: s.x ?? w.x,
    y: s.y ?? w.y,
    speed: s.speed ?? 1,
    status: s.status ?? "idle",
    is_active: s.is_active ?? true,
    version: s.version ?? 0,
    openAssignment: s.openAssignment ?? null,
    events: history(w.id, w.name, s),
  };
});

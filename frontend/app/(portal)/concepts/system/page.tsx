import { ConceptBanner } from "@/components/concepts/ConceptKit";
import { Annotation, PageHeader } from "@/components/portal/Wireframe";

import { SystemConsole } from "./SystemConsole";

export default function SystemConceptPage() {
  return (
    <div className="flex flex-col gap-4">
      <ConceptBanner target="Sprint 4 / stretch" buildsOn="/health, request-id logging, events log" />
      <PageHeader title="System health" subtitle="The backend at a glance · admin only" />
      <SystemConsole />
      <Annotation
        notes={{
          rules: [
            "One verdict at the top (healthy, degraded, down) with the reason and what to try, then one tile per service.",
            "Service tiles would come from a new GET /api/v1/system/health that wraps /health, a DB ping, the Alembic head and the assigner, simulator and generator loop timings.",
            "The request log reads the request ids core/request_logging.py already logs on arrival and completion; clicking a row shows both log lines and explains known error codes.",
            "Secrets are never shown: DATABASE_URL and keys are masked; config is read only.",
            "The routes table lists what exists on main, what is on a branch and what is planned. Gates are proposed: on main only /auth checks the Firebase token; feature/simulation adds a login check to its routers.",
          ],
          supervisor: "No access (redirected to /403). Sees the live/stale dot on the console.",
          admin: "Views health, the request log, events and config.",
        }}
      />
    </div>
  );
}

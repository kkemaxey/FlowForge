import { ConceptBanner } from "@/components/concepts/ConceptKit";
import { Annotation, PageHeader } from "@/components/portal/Wireframe";

import { WorkforceConcept } from "./WorkforceConcept";

export default function WorkforceConceptPage() {
  return (
    <div className="flex flex-col gap-4">
      <ConceptBanner target="Sprints 3–4" buildsOn="WorkforceManager, workforceLogic.ts, /api/v1/workers">
        The workforce panel, expanded with the open steps folded in: auth gates, a grid bound and per-worker history.
      </ConceptBanner>
      <PageHeader title="Workforce" subtitle="Admin view of /api/v1/workers · try a save, a stale save and a deactivate" />
      <WorkforceConcept />
      <Annotation
        notes={{
          rules: [
            "Same rules as main: every write is a compare-and-set on version; status, is_active and version are server-owned; a busy worker can't move; a worker with an open assignment can't be deactivated.",
            "Proposed: reads need a signed-in user and writes need require_supervisor (401 no token, 404 not provisioned, 403 not a supervisor).",
            "Proposed: positions must sit inside the floor, from WAREHOUSE_WIDTH and WAREHOUSE_HEIGHT, or 422 position_off_grid.",
            "Proposed: GET /api/v1/workers/{id}/events for the history panel, reading worker_* and task_* rows for that worker.",
            "The last-exchange panel shows the exact request and response, in the {detail, code} error format.",
          ],
          supervisor: "No access to this admin page (redirected to /403); the console panel stays.",
          admin: "Adds, edits and deactivates workers.",
        }}
      />
    </div>
  );
}

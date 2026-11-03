import { ConceptBanner } from "@/components/concepts/ConceptKit";
import { Annotation, PageHeader } from "@/components/portal/Wireframe";

import { BackendConsole } from "./BackendConsole";

export default function BackendConceptPage() {
  return (
    <div className="flex flex-col gap-4">
      <ConceptBanner target="Sprints 3–5" buildsOn="workforce module, Dockerfile, CI, tests">
        Trent&apos;s backend lane on one page: what&apos;s still open, what it waits on, and what main has today.
      </ConceptBanner>
      <PageHeader title="Backend console" subtitle="Workforce, deploy, CI and tests · admin only" />
      <BackendConsole />
      <Annotation
        notes={{
          rules: [
            "Only open steps are listed; finished work (workforce CRUD, migration 0003, request logging, CI MySQL and docker jobs) is shown only where it frames a gap.",
            "Route gates follow the design doc: reads need a signed-in user (401), writes need the supervisor role (403); /health stays public.",
            "“Main today” and the event and column tables reflect the code at 25605ca and feature/simulation; statuses and ticks are mock.",
            "In a live version the open steps would come from GitHub issues, CI from the Actions API, and route gates from FastAPI's OpenAPI schema.",
          ],
          supervisor: "No access (redirected to /403).",
          admin: "Views the page; ticks and decisions are local until wired to issues.",
        }}
      />
    </div>
  );
}

import { PlaceholderPage } from "@/components/portal/Wireframe";
import { DEMO_WAREHOUSE as warehouse } from "@/mocks/demoWarehouse";

export default function WorkforcePage() {
  return (
    <PlaceholderPage
      title="Workforce"
      subtitle={warehouse.name}
      elements={["Worker and robot list", "Create/edit form: name, kind, speed, start position", "Validation messages next to each field"]}
      notes={{
        rules: ["kind is human or robot; default speed about 1.0 m/s for humans, faster for robots.", "Start position must be a walkable cell inside the grid."],
        supervisor: "No access (redirected to /403).",
        admin: "Creates, edits and disables workers.",
      }}
    />
  );
}

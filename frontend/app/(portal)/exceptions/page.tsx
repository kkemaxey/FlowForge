import { PlaceholderPage } from "@/components/portal/Wireframe";
import { DEMO_WAREHOUSE as warehouse } from "@/mocks/demoWarehouse";

export default function ExceptionsPage() {
  return (
    <PlaceholderPage
      title="Exceptions"
      subtitle={warehouse.name}
      elements={["Open exceptions (type, task, location, raised at)", "Resolved exceptions", "Auto-reassignment trail per exception", "Acknowledge action"]}
      notes={{
        rules: [
          "Types: stockout and worker down (jam) for MVP.",
          "A stockout puts the task in exception; it is reassigned automatically once cleared.",
          "Resolved exceptions keep resolved_at and the resolution note.",
        ],
        supervisor: "Views and acknowledges exceptions.",
        admin: "Same as supervisor; injects test exceptions from the Simulation page.",
      }}
    />
  );
}

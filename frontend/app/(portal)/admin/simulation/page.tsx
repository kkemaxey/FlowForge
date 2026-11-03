import { PlaceholderPage } from "@/components/portal/Wireframe";
import { DEMO_WAREHOUSE as warehouse } from "@/mocks/demoWarehouse";

export default function SimulationPage() {
  return (
    <PlaceholderPage
      title="Simulation control"
      subtitle={warehouse.name}
      elements={["Order rate", "Sim speed: 1×, 10×, 60×", "Start / pause / reset", "Inject stockout or jam"]}
      notes={{
        rules: ["Each start creates a sim_runs row with its algorithm and seed.", "Reset clears orders and tasks for this warehouse only."],
        supervisor: "No access (redirected to /403).",
        admin: "Runs the simulation.",
      }}
    />
  );
}

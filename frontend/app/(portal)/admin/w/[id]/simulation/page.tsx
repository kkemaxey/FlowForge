import { PlaceholderPage } from "@/components/portal/Wireframe";
import { warehouseOr404 } from "@/mocks/warehouses";

export default async function SimulationPage({ params }: PageProps<"/admin/w/[id]/simulation">) {
  const warehouse = warehouseOr404((await params).id);

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

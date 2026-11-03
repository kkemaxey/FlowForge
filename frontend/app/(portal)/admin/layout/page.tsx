import { PlaceholderPage } from "@/components/portal/Wireframe";
import { DEMO_WAREHOUSE as warehouse } from "@/mocks/demoWarehouse";

export default function LayoutEditorPage() {
  return (
    <PlaceholderPage
      title="Layout editor"
      subtitle={warehouse.name}
      elements={["Cell palette: storage, aisle, station, blocked", "Grid canvas to paint cells", "Auto-generate location codes", "Import JSON"]}
      notes={{
        rules: ["Shrinking is blocked if a location would fall outside the grid.", "At most one location per storage cell; codes unique per warehouse.", "Cell types are display-only until pathfinding (stretch)."],
        supervisor: "No access (redirected to /403).",
        admin: "Edits the layout.",
      }}
    />
  );
}

import { PlaceholderPage } from "@/components/portal/Wireframe";

export default function NewWarehousePage() {
  return (
    <PlaceholderPage
      title="New warehouse"
      elements={["Name", "Width × height (cells)", "Cell size (m), default 1.0", "Import from JSON (warehouse-map.json)", "Validation messages next to each field"]}
      notes={{
        rules: ["Width 5 to 60, height 5 to 40.", "Name is required.", "Creates an empty layout of aisle cells to paint next."],
        supervisor: "No access (redirected to /403).",
        admin: "Creates warehouses.",
      }}
    />
  );
}

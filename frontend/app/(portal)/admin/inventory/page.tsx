import { PlaceholderPage } from "@/components/portal/Wireframe";
import { DEMO_WAREHOUSE as warehouse } from "@/mocks/demoWarehouse";

export default function InventoryPage() {
  return (
    <PlaceholderPage
      title="SKUs and inventory"
      subtitle={warehouse.name}
      elements={["SKU catalog (code, name)", "Stock per location (on hand, reserved)", "CSV import"]}
      notes={{
        rules: ["Inventory is keyed by (location_id, sku_id).", "Reserved can never exceed on hand."],
        supervisor: "No access (redirected to /403).",
        admin: "Manages SKUs and stock.",
      }}
    />
  );
}

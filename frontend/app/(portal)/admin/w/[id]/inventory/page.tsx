import { PlaceholderPage } from "@/components/portal/Wireframe";
import { warehouseOr404 } from "@/mocks/warehouses";

export default async function InventoryPage({ params }: PageProps<"/admin/w/[id]/inventory">) {
  const warehouse = warehouseOr404((await params).id);

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

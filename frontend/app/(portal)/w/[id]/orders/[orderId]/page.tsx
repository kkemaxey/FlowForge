import { PlaceholderPage } from "@/components/portal/Wireframe";
import { warehouseOr404 } from "@/mocks/warehouses";

export default async function OrderDetailPage({ params }: PageProps<"/w/[id]/orders/[orderId]">) {
  const { id, orderId } = await params;
  const warehouse = warehouseOr404(id);

  return (
    <PlaceholderPage
      title={`Order #${orderId}`}
      subtitle={`${warehouse.name} · opens as a drawer over the console in the final build`}
      elements={["Order lines (SKU, qty, location)", "Tasks per line with status and worker", "Status timeline", "Expedite button"]}
      notes={{
        rules: [
          "Statuses: new → in_progress → complete, or late once past due_at.",
          "Expedite raises the order's priority so the assigner picks its tasks first.",
          "Can't expedite a complete order.",
        ],
        supervisor: "Views the order and expedites it.",
        admin: "Same as supervisor.",
      }}
    />
  );
}

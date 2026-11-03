import { PlaceholderPage } from "@/components/portal/Wireframe";

export default function UsersPage() {
  return (
    <PlaceholderPage
      title="Users and roles"
      elements={["User list (email, role)", "Invite by email", "Set role: admin or supervisor", "Warehouse access (user_warehouses)"]}
      notes={{
        rules: ["users.role is admin or supervisor.", "Can't remove the last admin.", "Invites go through Firebase Auth."],
        supervisor: "No access (redirected to /403).",
        admin: "Invites users, sets roles and warehouse access.",
      }}
    />
  );
}

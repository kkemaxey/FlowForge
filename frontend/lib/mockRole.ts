import type { Role } from "@/types";

// Dev-only role switch for the wireframes. Until Firebase custom claims carry users.role, the portal reads
// the role from this cookie so the demo can show both the admin and supervisor views. The header toggle
// writes it, and proxy.ts reads it to block /admin/* for supervisors.
//
// This is NOT security: the FastAPI require_role("admin") dependency is the real gate.

export const ROLE_COOKIE = "ff_mock_role";

// The toggle only shows while the app runs on mock data.
export const ROLE_TOGGLE_ENABLED = (process.env.NEXT_PUBLIC_USE_MOCKS ?? "true") === "true";

/** Missing or unknown cookie values fall back to the least-privileged role. */
export function parseRole(value: string | undefined): Role {
  return value === "admin" ? "admin" : "supervisor";
}

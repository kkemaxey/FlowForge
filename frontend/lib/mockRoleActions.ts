"use server";

import { cookies } from "next/headers";

import type { Role } from "@/types";

import { ROLE_COOKIE } from "./mockRole";

/** Saves the dev-only mock role (see mockRole.ts). */
export async function setMockRole(role: Role) {
  (await cookies()).set(ROLE_COOKIE, role, { path: "/", maxAge: 60 * 60 * 24 * 365, sameSite: "lax" });
}

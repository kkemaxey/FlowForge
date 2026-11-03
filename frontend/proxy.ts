import { NextResponse, type NextRequest } from "next/server";

import { parseRole, ROLE_COOKIE } from "@/lib/mockRole";

// Sends supervisors who open a Setup page (/admin/*) to /403. This only spares them a page they can't use;
// the backend's require_role("admin") check is what actually protects admin data.
export function proxy(request: NextRequest) {
  if (parseRole(request.cookies.get(ROLE_COOKIE)?.value) !== "admin") {
    return NextResponse.redirect(new URL("/403", request.url));
  }
  return NextResponse.next();
}

export const config = {
  // The concept wireframes are admin-only, like the Setup pages.
  matcher: ["/admin/:path*", "/concepts", "/concepts/:path*"],
};

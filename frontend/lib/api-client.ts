import { getFirebaseAuth } from "@/lib/firebase";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type ApiOptions = RequestInit & { auth?: boolean };

/** One entry of a 422 body's `errors` list (FastAPI validation), e.g. `loc: ["body", "x"]`. */
export interface ApiFieldError {
  loc: (string | number)[];
  msg: string;
  type?: string;
}

/**
 * Thrown by apiFetch for any non-OK response. `message` stays `"<METHOD> <path> failed: <status>"`;
 * `code` and `detail` come from the backend's `{"detail", "code"}` error body when it has one.
 */
export class ApiRequestError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly detail?: string;
  readonly errors?: ApiFieldError[];

  constructor(message: string, status: number, body?: { code?: string; detail?: string; errors?: ApiFieldError[] }) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = body?.code;
    this.detail = body?.detail;
    this.errors = body?.errors;
  }
}

/** Fetch a backend path as JSON, attaching the signed-in user's Firebase token by default. */
export async function apiFetch<T>(path: string, { auth = true, ...init }: ApiOptions = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");

  if (auth) {
    const token = await getFirebaseAuth().currentUser?.getIdToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    // Error bodies are {"detail", "code"} JSON; anything else (e.g. a proxy's HTML page) is ignored.
    let body: { code?: string; detail?: string; errors?: ApiFieldError[] } | undefined;
    try {
      const parsed: unknown = await response.json();
      if (parsed && typeof parsed === "object") body = parsed as typeof body;
    } catch {
      body = undefined;
    }
    throw new ApiRequestError(`${init.method ?? "GET"} ${path} failed: ${response.status}`, response.status, {
      code: typeof body?.code === "string" ? body.code : undefined,
      detail: typeof body?.detail === "string" ? body.detail : undefined,
      errors: Array.isArray(body?.errors) ? body.errors : undefined,
    });
  }
  // 204 No Content (e.g. DELETE) has no body to parse.
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function getHealth() {
  return apiFetch<{ status: string }>("/health", { auth: false });
}

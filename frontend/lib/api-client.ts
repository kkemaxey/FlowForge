import { FIREBASE_CONFIGURED, getFirebaseAuth } from "@/lib/firebase";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type ApiOptions = RequestInit & { auth?: boolean };

/**
 * Fetch a backend path as JSON, attaching the signed-in user's Firebase token by default. Without Firebase
 * config the request goes out with no token, so local development works before login is set up.
 */
export async function apiFetch<T>(path: string, { auth = true, ...init }: ApiOptions = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");

  if (auth && FIREBASE_CONFIGURED) {
    const token = await getFirebaseAuth().currentUser?.getIdToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new Error(`${init.method ?? "GET"} ${path} failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getHealth() {
  return apiFetch<{ status: string }>("/health", { auth: false });
}

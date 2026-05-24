export type AuthMode = "pending" | "guest" | "authenticated";

export interface AuthState {
  mode: AuthMode;
  apiKey: string | null;
}

const STORAGE_KEY = "rcp_auth";

export function loadAuth(): AuthState {
  if (typeof window === "undefined") return { mode: "pending", apiKey: null };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { mode: "pending", apiKey: null };
    const parsed = JSON.parse(raw) as { mode?: unknown; apiKey?: unknown };
    if (parsed.mode === "authenticated" && typeof parsed.apiKey === "string") {
      return { mode: "authenticated", apiKey: parsed.apiKey };
    }
    if (parsed.mode === "guest") {
      return { mode: "guest", apiKey: null };
    }
  } catch {
    // ignore malformed storage
  }
  return { mode: "pending", apiKey: null };
}

export function saveAuth(auth: AuthState): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(auth));
}

export function clearAuth(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(STORAGE_KEY);
}

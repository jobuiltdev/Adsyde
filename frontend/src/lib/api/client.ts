import type { ApiErrorBody } from "@/lib/types";

const API_BASE = "/backend/api/v1";
const REFRESH_KEY = "adsyde.refresh";
let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

function detailText(detail: unknown): string | null {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(detailText).filter(Boolean).join(" ");
  if (detail && typeof detail === "object") return detailText(Object.values(detail)[0]);
  return null;
}

export function errorMessage(code: string, detail: unknown): string {
  const safe: Record<string, string> = { throttled: "Too many requests. Please wait and try again.", not_authenticated: "Your session has expired. Please sign in again.", authentication_failed: "Your session has expired. Please sign in again.", not_found: "We couldn't find that item.", permission_denied: "You don't have access to that item.", generation_limit_reached: "You already have the maximum number of active generations.", INSUFFICIENT_CREDITS: "You do not have enough available credits for this generation." };
  return safe[code] ?? detailText(detail) ?? "Something went wrong. Please try again.";
}

export class ApiError extends Error {
  constructor(public status: number, public code: string, public detail: unknown) { super(errorMessage(code, detail)); this.name = "ApiError"; }
}
const storedRefresh = () => typeof window === "undefined" ? null : sessionStorage.getItem(REFRESH_KEY);
export const hasRefreshSession = () => Boolean(storedRefresh());
export function setSession(tokens: { access: string; refresh: string }): void { accessToken = tokens.access; sessionStorage.setItem(REFRESH_KEY, tokens.refresh); }
export function clearSession(): void { accessToken = null; if (typeof window !== "undefined") { sessionStorage.removeItem(REFRESH_KEY); window.dispatchEvent(new Event("adsyde:logout")); } }
async function parseError(response: Response) { const body = await response.json().catch(() => ({})) as ApiErrorBody; return new ApiError(response.status, body.error?.code ?? `http_${response.status}`, body.error?.detail); }
async function refreshAccess(): Promise<string | null> {
  const refresh = storedRefresh(); if (!refresh) return null;
  const response = await fetch(`${API_BASE}/auth/refresh/`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh }) });
  if (!response.ok) { clearSession(); return null; }
  const tokens = await response.json() as { access: string; refresh?: string }; accessToken = tokens.access;
  if (tokens.refresh) sessionStorage.setItem(REFRESH_KEY, tokens.refresh); return accessToken;
}
export async function api<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  if (!accessToken && storedRefresh()) { refreshPromise ??= refreshAccess().finally(() => { refreshPromise = null; }); await refreshPromise; }
  const headers = new Headers(init.headers); if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json"); if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (response.status === 401 && retry && storedRefresh()) { refreshPromise ??= refreshAccess().finally(() => { refreshPromise = null; }); if (await refreshPromise) return api<T>(path, init, false); }
  if (!response.ok) throw await parseError(response); if (response.status === 204) return undefined as T; return response.json() as Promise<T>;
}
export async function authenticatedBlob(path: string): Promise<Blob> {
  if (!accessToken && storedRefresh()) await refreshAccess();
  const response = await fetch(`${API_BASE}${path}`, { headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {} });
  if (!response.ok) throw await parseError(response); return response.blob();
}

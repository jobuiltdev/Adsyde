"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api/resources";
import { clearSession, hasRefreshSession, setSession } from "@/lib/api/client";
import type { User } from "@/lib/types";

type AuthState = { user: User | null; loading: boolean; login(email: string, password: string): Promise<void>; logout(): Promise<void> };
const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null); const [loading, setLoading] = useState(true); const router = useRouter();
  const load = useCallback(async () => { if (!hasRefreshSession()) { setLoading(false); return; } try { setUser(await authApi.me()); } catch { clearSession(); setUser(null); } finally { setLoading(false); } }, []);
  useEffect(() => { queueMicrotask(() => void load()); const reset = () => setUser(null); window.addEventListener("adsyde:logout", reset); return () => window.removeEventListener("adsyde:logout", reset); }, [load]);
  async function login(email: string, password: string) { setSession(await authApi.login(email, password)); setUser(await authApi.me()); }
  async function logout() { const refresh = sessionStorage.getItem("adsyde.refresh"); try { if (refresh) await authApi.logout(refresh); } finally { clearSession(); setUser(null); router.replace("/login"); } }
  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}
export function useAuth() { const value = useContext(AuthContext); if (!value) throw new Error("AuthProvider is required"); return value; }

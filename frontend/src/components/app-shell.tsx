"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { creditsApi } from "@/lib/api/resources";
import { useAuth } from "@/lib/auth/auth-context";
import { Button, Skeleton } from "./ui";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const [available, setAvailable] = useState<number | null>(null);
  const router = useRouter();
  const path = usePathname();
  useEffect(() => {
    if (!loading && !user) router.replace(`/login?next=${encodeURIComponent(path)}`);
    if (user) creditsApi.wallet().then((wallet) => setAvailable(wallet.available)).catch(() => {});
  }, [loading, user, router, path]);
  if (loading || !user) return <main className="page"><Skeleton lines={5} /></main>;
  return <div className="app-layout">
    <aside className="sidebar">
      <Link className="brand" href="/app">Adsyde<span className="brand-dot">.</span></Link>
      <nav className="nav" aria-label="Main navigation">
        <Link href="/app">Overview</Link><Link href="/app/projects">Projects</Link>
        <Link href="/app/projects/new">New project</Link><Link href="/app/credits">Credit activity</Link>
      </nav>
      <div className="sidebar-foot"><strong>{available === null ? "Credits unavailable" : `${available.toLocaleString()} credits`}</strong><small>{user.email}</small></div>
    </aside>
    <div className="app-main"><header className="app-header"><span className="eyebrow">Creative workspace</span><Button variant="secondary" onClick={() => void logout()}>Log out</Button></header>{children}</div>
  </div>;
}

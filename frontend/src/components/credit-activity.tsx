"use client";

import { useEffect, useState } from "react";
import { creditsApi } from "@/lib/api/resources";
import type { CreditTransaction, CreditWallet } from "@/lib/types";
import { creditActivityAmount } from "@/lib/credits";
import { Notice, Skeleton } from "./ui";

export function CreditActivity() {
  const [wallet, setWallet] = useState<CreditWallet | null>(null);
  const [items, setItems] = useState<CreditTransaction[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([creditsApi.wallet(), creditsApi.transactions()])
      .then(([walletResult, transactionResult]) => {
        setWallet(walletResult);
        setItems(transactionResult.results);
      })
      .catch(() => setError("Credit activity could not be loaded."));
  }, []);
  if (!wallet && !error) return <main className="page"><Skeleton lines={6} /></main>;
  return <main className="page">
    <div className="page-head"><div><p className="eyebrow">Credits</p><h1>Credit activity</h1><p>Your available credits and recent account activity.</p></div></div>
    {error && <Notice kind="error">{error}</Notice>}
    {wallet && <div className="grid">
      <div className="card"><p>Available credits</p><h2>{wallet.available.toLocaleString()}</h2></div>
      <div className="card"><p>Total balance</p><h2>{wallet.balance.toLocaleString()}</h2></div>
      <div className="card"><p>In active generations</p><h2>{wallet.reserved.toLocaleString()}</h2></div>
    </div>}
    <section className="section card"><h2>Recent activity</h2><div className="generation-list">
      {items.map((item) => <div className="generation-row" key={item.id}><div><strong>{item.reason}</strong><small>{new Date(item.created_at).toLocaleString()}</small></div><strong>{creditActivityAmount(item.amount, item.reserved_change) > 0 ? "+" : ""}{creditActivityAmount(item.amount, item.reserved_change)} credits</strong></div>)}
    </div></section>
  </main>;
}

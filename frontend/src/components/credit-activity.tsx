"use client";

import { useEffect, useState } from "react";
import { creditsApi, paymentsApi } from "@/lib/api/resources";
import type { CreditPackage, CreditTransaction, CreditWallet, Payment } from "@/lib/types";
import { creditActivityAmount } from "@/lib/credits";
import { formatNgn, safeCheckoutUrl } from "@/lib/payments";
import { Button, Notice, Skeleton } from "./ui";

export function CreditActivity() {
  const [wallet, setWallet] = useState<CreditWallet | null>(null);
  const [items, setItems] = useState<CreditTransaction[]>([]);
  const [packages, setPackages] = useState<CreditPackage[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [buying, setBuying] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all([
      creditsApi.wallet(),
      creditsApi.transactions(),
      paymentsApi.packages(),
      paymentsApi.list(),
    ])
      .then(([walletResult, transactionResult, packageResult, paymentResult]) => {
        setWallet(walletResult);
        setItems(transactionResult.results);
        setPackages(packageResult);
        setPayments(paymentResult.results);
      })
      .catch(() => setError("Credit activity could not be loaded."));
  }, []);
  async function buy(packageKey: string) {
    setBuying(packageKey);
    setError("");
    try {
      const payment = await paymentsApi.initialize(packageKey, crypto.randomUUID());
      if (!payment.authorization_url || !safeCheckoutUrl(payment.authorization_url)) {
        throw new Error("Secure checkout could not be opened.");
      }
      window.location.assign(payment.authorization_url);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Payment could not be initialized.");
      setBuying("");
    }
  }
  if (!wallet && !error) return <main className="page"><Skeleton lines={6} /></main>;
  return <main className="page">
    <div className="page-head"><div><p className="eyebrow">Credits</p><h1>Credit activity</h1><p>Your available credits and recent account activity.</p></div></div>
    {error && <Notice kind="error">{error}</Notice>}
    {wallet && <div className="grid">
      <div className="card"><p>Available credits</p><h2>{wallet.available.toLocaleString()}</h2></div>
      <div className="card"><p>Total balance</p><h2>{wallet.balance.toLocaleString()}</h2></div>
      <div className="card"><p>In active generations</p><h2>{wallet.reserved.toLocaleString()}</h2></div>
    </div>}
    <section className="section" id="buy-credits"><div className="section-head"><h2>Buy credits</h2></div><div className="grid">
      {packages.map((item) => <div className="card credit-package-card" key={item.key}><p className="eyebrow">{item.name}</p><h2>{item.credits.toLocaleString()} credits</h2><p>{formatNgn(item.amount_minor)}</p><Button disabled={Boolean(buying)} onClick={() => void buy(item.key)}>{buying === item.key ? "Opening secure checkout…" : "Buy credits"}</Button></div>)}
    </div><p className="muted">Development package values are placeholders, not final pricing.</p></section>
    <section className="section card"><h2>Recent activity</h2><div className="generation-list">
      {items.map((item) => <div className="generation-row" key={item.id}><div><strong>{item.reason}</strong><small>{new Date(item.created_at).toLocaleString()}</small></div><strong>{creditActivityAmount(item.amount, item.reserved_change) > 0 ? "+" : ""}{creditActivityAmount(item.amount, item.reserved_change)} credits</strong></div>)}
    </div></section>
    <section className="section card"><h2>Payment attempts</h2><div className="generation-list">
      {payments.map((payment) => <div className="generation-row" key={payment.id}><div><strong>{payment.package_name}</strong><small>{payment.internal_reference}</small></div><span className={`badge status-${payment.status}`}>{payment.status.replaceAll("_", " ")}</span><strong>{formatNgn(payment.amount_minor)}</strong></div>)}
    </div></section>
  </main>;
}

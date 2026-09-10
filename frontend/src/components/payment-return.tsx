"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { paymentsApi, creditsApi } from "@/lib/api/resources";
import type { Payment } from "@/lib/types";
import { paymentIsPending } from "@/lib/payments";
import { Notice, Skeleton } from "./ui";

export function PaymentReturn() {
  const search = useSearchParams();
  const paymentId = search.get("payment_id");
  const [payment, setPayment] = useState<Payment | null>(null);
  const [message, setMessage] = useState("");
  useEffect(() => {
    if (!paymentId) {
      return;
    }
    let stopped = false;
    let attempts = 0;
    async function check() {
      try {
        const result = await paymentsApi.verify(paymentId as string);
        if (stopped) return;
        setPayment(result);
        if (result.status === "succeeded") {
          await creditsApi.wallet();
          return;
        }
        if (paymentIsPending(result.status) && attempts++ < 10) {
          window.setTimeout(check, 3000);
        } else if (paymentIsPending(result.status)) {
          setMessage("Your payment is still being confirmed. Your credits will appear automatically once verification completes.");
        }
      } catch {
        if (!stopped) setMessage("Your payment could not be confirmed yet.");
      }
    }
    void check();
    return () => { stopped = true; };
  }, [paymentId]);
  if (!paymentId) {
    return <main className="page"><Notice kind="error">The payment reference is missing.</Notice></main>;
  }
  if (!payment && !message) return <main className="page"><Skeleton lines={4} /></main>;
  return <main className="page"><div className="card">
    {payment?.status === "succeeded" ? <Notice kind="success">Payment confirmed. {payment.credits} credits were added.</Notice> : payment?.status === "failed" || payment?.status === "review_required" ? <Notice kind="error">Payment was not credited. No additional charge attempt will be started automatically.</Notice> : <Notice>{message || "Confirming payment…"}</Notice>}
    <Link className="button secondary" href="/app/credits">Return to credit activity</Link>
  </div></main>;
}

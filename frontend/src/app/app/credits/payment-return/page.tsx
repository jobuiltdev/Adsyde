import { Suspense } from "react";
import { PaymentReturn } from "@/components/payment-return";
import { Skeleton } from "@/components/ui";

export default function PaymentReturnPage() {
  return <Suspense fallback={<main className="page"><Skeleton lines={4} /></main>}><PaymentReturn /></Suspense>;
}

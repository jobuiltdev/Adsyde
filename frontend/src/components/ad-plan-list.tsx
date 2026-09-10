"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { adPlansApi } from "@/lib/api/resources";
import type { AdPlan } from "@/lib/types";

export function AdPlanList({ projectId }: { projectId: string }) {
  const [plans, setPlans] = useState<AdPlan[]>([]);
  useEffect(() => { adPlansApi.list(projectId).then(setPlans).catch(() => {}); }, [projectId]);
  if (!plans.length) return <div className="empty"><p>No guided ad plans yet.</p><Link className="button primary" href={`/app/projects/${projectId}/create?mode=guided`}>Start guided ad</Link></div>;
  return <div className="generation-list">{plans.map((plan) => <Link className="generation-row" key={plan.id} href={`/app/projects/${projectId}/create?mode=guided&plan=${plan.id}`}><div><strong>{plan.business_product}</strong><small>{plan.offer_objective || plan.platform.replaceAll("_", " ")}</small></div><span className={`badge status-${plan.status}`}>{plan.status}</span></Link>)}</div>;
}

import Link from "next/link";
import { AdBuilder } from "@/components/ad-builder";
import { PromptStudio } from "@/components/prompt-studio";

export default async function CreatePage({ params, searchParams }: { params: Promise<{ projectId: string }>; searchParams: Promise<{ mode?: string; plan?: string }> }) {
  const { projectId } = await params;
  const query = await searchParams;
  if (query.mode === "guided") return <AdBuilder projectId={projectId} resumeId={query.plan} />;
  if (query.mode === "prompt") return <PromptStudio projectId={projectId} />;
  return <main className="page"><div className="page-head"><div><p className="eyebrow">Create Ad</p><h1>How do you want to begin?</h1><p>Both paths keep the final prompt in your hands.</p></div></div><div className="grid">
    <Link className="card card-link project-card" href={`/app/projects/${projectId}/create?mode=guided`}><p className="eyebrow">Guided Builder</p><h2>Structure the ad with Adsyde</h2><p>Describe the product, audience, offer, and style. Review every part before generating.</p></Link>
    <Link className="card card-link project-card" href={`/app/projects/${projectId}/create?mode=prompt`}><p className="eyebrow">Prompt Studio</p><h2>Start from your own prompt</h2><p>Write and control the exact creative direction yourself.</p></Link>
  </div></main>;
}

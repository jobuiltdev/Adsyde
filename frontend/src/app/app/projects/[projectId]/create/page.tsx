import { AdBuilder } from "@/components/ad-builder";
import { CreationModeChoice } from "@/components/creation-mode-choice";
import { PromptStudio } from "@/components/prompt-studio";

export default async function CreatePage({ params, searchParams }: { params: Promise<{ projectId: string }>; searchParams: Promise<{ mode?: string; plan?: string }> }) {
  const { projectId } = await params;
  const query = await searchParams;
  if (query.mode === "guided") return <AdBuilder projectId={projectId} resumeId={query.plan} />;
  if (query.mode === "prompt") return <PromptStudio projectId={projectId} />;
  return <CreationModeChoice projectId={projectId} />;
}

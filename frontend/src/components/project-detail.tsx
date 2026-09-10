"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { projectsApi } from "@/lib/api/resources";
import type { Project } from "@/lib/types";
import { AdPlanList } from "./ad-plan-list";
import { AssetManager } from "./asset-manager";
import { GenerationHistory } from "./generation-history";
import { Button, Dialog, Notice, Skeleton } from "./ui";

export function ProjectDetail({ id }: { id: string }) {
  const [project, setProject] = useState<Project | null>(null);
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState(false);
  const router = useRouter();
  useEffect(() => { projectsApi.get(id).then(setProject).catch((reason) => setError(reason.message)); }, [id]);
  async function remove() {
    try { await projectsApi.remove(id); router.replace("/app/projects"); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Project could not be deleted."); }
  }
  if (error && !project) return <main className="page"><Notice kind="error">{error}</Notice><Link href="/app/projects">Back to projects</Link></main>;
  if (!project) return <main className="page"><Skeleton lines={6} /></main>;
  return <main className="page">
    <div className="page-head"><div><p className="eyebrow">{project.business_name || "Project"}</p><h1>{project.name}</h1><p>{project.description || "Build a visual direction, then bring it to life."}</p></div><div className="top-actions"><Link className="button secondary" href={`/app/projects/${id}/edit`}>Edit</Link><Link className="button primary" href={`/app/projects/${id}/create`}>Create Ad</Link></div></div>
    <section className="section"><div className="section-head"><h2>Ad plans</h2></div><AdPlanList projectId={id} /></section>
    <section className="section"><div className="section-head"><h2>Assets</h2></div><AssetManager projectId={id} /></section>
    <section className="section"><div className="section-head"><h2>Generation history</h2></div><GenerationHistory projectId={id} /></section>
    <section className="section card"><h2>Project settings</h2><p>Deleting this project permanently removes its creative workspace. Financial records retain immutable references.</p><Button variant="danger" onClick={() => setConfirming(true)}>Delete project</Button></section>
    <Dialog open={confirming} title="Delete this project?" onClose={() => setConfirming(false)}><p>This removes <strong>{project.name}</strong> and its creative files. Financial records remain preserved.</p><div className="top-actions"><Button variant="secondary" onClick={() => setConfirming(false)}>Keep project</Button><Button variant="danger" onClick={() => void remove()}>Delete project</Button></div></Dialog>
  </main>;
}

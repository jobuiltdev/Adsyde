"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { assetsApi, generationsApi, projectsApi } from "@/lib/api/resources";
import type { Asset, GenerationOptions, Project } from "@/lib/types";
import { effectivePrompt, type PromptMode } from "@/lib/prompt";
import { safeGenerationSelection, validGenerationSelection } from "@/lib/generation-options";
import { Button, Notice, Skeleton, Textarea } from "./ui";
import { PrivateImage } from "./private-media";

export function PromptStudio({ projectId }: { projectId: string }) {
  const [project, setProject] = useState<Project | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [options, setOptions] = useState<GenerationOptions | null>(null);
  const [mode, setMode] = useState<PromptMode>("exact");
  const [prompt, setPrompt] = useState("");
  const [modelKey, setModelKey] = useState("");
  const [ratio, setRatio] = useState<"9:16" | "1:1" | "16:9">("9:16");
  const [duration, setDuration] = useState(10);
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [optionsError, setOptionsError] = useState("");
  const router = useRouter();

  useEffect(() => {
    Promise.all([projectsApi.get(projectId), assetsApi.list(projectId)])
      .then(([projectResult, assetResult]) => {
        setProject(projectResult);
        setAssets(assetResult.results);
      })
      .catch((reason: Error) => setError(reason.message));
    generationsApi
      .options()
      .then((result) => {
        if (!result.models.length) throw new Error("Generation is not currently available.");
        setOptions(result);
        const first = result.models[0];
        setModelKey(first.key);
        setRatio(first.aspect_ratios[0]);
        setDuration(first.durations[0]);
      })
      .catch(() =>
        setOptionsError("Generation options could not be loaded. Please try again later."),
      );
  }, [projectId]);

  const model = useMemo(
    () => options?.models.find((item) => item.key === modelKey),
    [modelKey, options],
  );

  function selectModel(key: string) {
    const next = options?.models.find((item) => item.key === key);
    if (!next) return;
    const safe = safeGenerationSelection(next, ratio, duration);
    setModelKey(key);
    setRatio(safe.ratio);
    setDuration(safe.duration);
  }

  const toggle = (id: string) =>
    setSelected((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    );

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!prompt.trim() || !model || !validGenerationSelection(model, ratio, duration)) {
      setError("Write a prompt and choose an available generation setup.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const generation = await generationsApi.create(projectId, {
        prompt: effectivePrompt(prompt, mode),
        aspect_ratio: ratio,
        duration_seconds: duration,
        model: model.key,
      });
      router.push(`/app/projects/${projectId}/generations/${generation.id}`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Generation could not be started.");
      setBusy(false);
    }
  }

  const mediaLoad = useCallback((id: string) => assetsApi.content(projectId, id), [projectId]);
  if (!project && !error) return <main className="page"><Skeleton lines={6} /></main>;

  return <main className="page">
    <div className="page-head"><div><p className="eyebrow">Prompt Studio · {project?.name}</p><h1>Direct the idea.</h1><p>Your words stay under your control.</p></div></div>
    {error && <Notice kind="error">{error}</Notice>}
    {optionsError && <Notice kind="error">{optionsError}</Notice>}
    <form className="studio" onSubmit={submit}>
      <section className="studio-main">
        <Textarea label="Describe the video you want to create" value={prompt} onChange={(event) => setPrompt(event.target.value)} maxLength={4000} hint={`${prompt.length}/4000 characters`} />
        <div className="section"><h2>How should Adsyde use your prompt?</h2><div className="choice-grid">
          <button type="button" className={`choice ${mode === "exact" ? "selected" : ""}`} onClick={() => setMode("exact")} aria-pressed={mode === "exact"}><strong>Use exactly as written</strong><small>No additions or creative rewriting.</small></button>
          <button type="button" className={`choice ${mode === "enhance" ? "selected" : ""}`} onClick={() => setMode("enhance")} aria-pressed={mode === "enhance"}><strong>Enhance my prompt</strong><small>Adds a transparent, deterministic creative direction in this development version.</small></button>
        </div>{mode === "enhance" && <Notice>Enhancement is a local development aid, not an AI service. Your original text remains visible above.</Notice>}</div>
        {options && <div className="section"><h2>Model</h2><div className="duration-row">{options.models.map((item) => <Button type="button" variant={modelKey === item.key ? "primary" : "secondary"} key={item.key} onClick={() => selectModel(item.key)}>{item.display_name}</Button>)}</div></div>}
        <div className="section"><h2>Format</h2><div className="ratio-row">{model?.aspect_ratios.map((item) => <button type="button" key={item} className={`ratio ${ratio === item ? "selected" : ""}`} onClick={() => setRatio(item)} aria-pressed={ratio === item}>{item}</button>)}</div></div>
        <div className="section"><h2>Duration</h2><div className="duration-row">{model?.durations.map((item) => <Button type="button" variant={duration === item ? "primary" : "secondary"} key={item} onClick={() => setDuration(item)} aria-pressed={duration === item}>{item}s</Button>)}</div></div>
        {assets.length > 0 && <div className="section"><h2>Reference assets <small className="muted">optional context</small></h2><p className="muted">Selections stay in this editing session; provider reference inputs are deferred.</p><div className="asset-grid">{assets.map((asset) => <label className="asset-choice" key={asset.id}><input type="checkbox" checked={selected.includes(asset.id)} onChange={() => toggle(asset.id)} /><PrivateImage load={() => mediaLoad(asset.id)} alt="" /><span>{asset.original_filename}</span></label>)}</div></div>}
      </section>
      <aside className="studio-side"><div className="card summary"><p className="eyebrow">Generation setup</p><h2>{ratio} video</h2><p>{duration} seconds · {model?.display_name ?? "Options loading"}</p><p>{mode === "exact" ? "Prompt stays exactly as written." : "Local enhancement is active."}</p><p>{selected.length} reference{selected.length === 1 ? "" : "s"} selected</p><Button style={{ width: "100%" }} disabled={busy || !prompt.trim() || !validGenerationSelection(model, ratio, duration) || Boolean(optionsError)}>{busy ? "Queueing generation…" : "Generate video"}</Button><small className="muted">Submitting once is enough. We’ll track uncertain jobs safely.</small></div></aside>
    </form>
  </main>;
}

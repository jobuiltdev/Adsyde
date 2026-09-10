"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { adPlansApi, assetsApi, creditsApi, generationsApi, projectsApi } from "@/lib/api/resources";
import type { AdPlan, Asset, CreditWallet, GenerationOptions, PlanRevision, Project } from "@/lib/types";
import { platformDefaults, roleForCategory } from "@/lib/ad-builder";
import { Button, Notice, Skeleton, Textarea } from "./ui";
import { PrivateImage } from "./private-media";

const styles = ["premium", "energetic", "minimal", "playful", "bold", "elegant", "warm", "professional"];
const platforms = ["instagram_reels", "tiktok", "instagram_feed", "youtube_shorts", "youtube", "general_social"];

export function AdBuilder({ projectId, resumeId }: { projectId: string; resumeId?: string }) {
  const [project, setProject] = useState<Project | null>(null);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [options, setOptions] = useState<GenerationOptions | null>(null);
  const [wallet, setWallet] = useState<CreditWallet | null>(null);
  const [plan, setPlan] = useState<AdPlan | null>(null);
  const [revision, setRevision] = useState<PlanRevision | null>(null);
  const [step, setStep] = useState(1);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ business_product:"", offer_objective:"", audience:"", style:"premium", style_notes:"", platform:"instagram_reels", call_to_action:"", selling_points:"", model:"mock-standard", aspect_ratio:"9:16" as "9:16"|"1:1"|"16:9", duration_seconds:10 });
  const [selected, setSelected] = useState<string[]>([]);
  const router = useRouter();

  useEffect(() => {
    Promise.all([projectsApi.get(projectId), assetsApi.list(projectId), generationsApi.options(), creditsApi.wallet()])
      .then(([projectResult, assetResult, optionResult, walletResult]) => {
        setProject(projectResult); setAssets(assetResult.results); setOptions(optionResult); setWallet(walletResult);
        if (!resumeId) setForm((value) => ({...value, business_product: projectResult.description || projectResult.business_name, audience: projectResult.target_audience, style_notes: projectResult.brand_style, model: optionResult.models[0].key, aspect_ratio: optionResult.models[0].aspect_ratios[0], duration_seconds: optionResult.models[0].durations[0]}));
      }).catch(() => setError("The guided builder could not be loaded."));
    if (resumeId) adPlansApi.get(projectId, resumeId).then((saved) => {
      setPlan(saved); setRevision(saved.revisions[0] || null); setSelected(saved.selected_assets.map((item) => item.asset_id));
      setForm({business_product:saved.business_product,offer_objective:saved.offer_objective,audience:saved.audience,style:saved.style,style_notes:saved.style_notes,platform:saved.platform,call_to_action:saved.call_to_action,selling_points:saved.selling_points.join("\n"),model:saved.model,aspect_ratio:saved.aspect_ratio,duration_seconds:saved.duration_seconds});
      if (saved.revisions.length) setStep(4);
    }).catch(() => setError("The saved ad plan could not be loaded."));
  }, [projectId, resumeId]);

  const model = options?.models.find((item) => item.key === form.model);
  const cost = model?.credit_prices[String(form.duration_seconds)];
  const short = wallet && cost ? Math.max(0, cost-wallet.available) : 0;
  const assetInputs = useMemo(() => selected.map((id, position) => {
    const asset = assets.find((item) => item.id === id)!;
    return {asset_id:id, role:roleForCategory(asset.category, position), position};
  }), [selected, assets]);
  const payload = {...form, selling_points:form.selling_points.split("\n").map((item)=>item.trim()).filter(Boolean), selected_asset_inputs:assetInputs};

  async function save() {
    if (!form.business_product.trim()) { setError("Tell us what you are advertising."); return null; }
    setBusy(true); setError("");
    try {
      const saved = plan ? await adPlansApi.update(projectId, plan.id, payload) : await adPlansApi.create(projectId, payload);
      setPlan(saved); return saved;
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Draft could not be saved."); return null; }
    finally { setBusy(false); }
  }
  async function next() { const saved=await save(); if(saved) setStep((value)=>Math.min(4,value+1)); }
  async function makePlan() {
    const saved=await save(); if(!saved)return;
    setBusy(true); try { const result=await adPlansApi.plan(projectId,saved.id,crypto.randomUUID());setRevision(result);setStep(4); } catch(reason){setError(reason instanceof Error?reason.message:"Ad plan could not be generated.");} finally{setBusy(false);}
  }
  async function persistRevision() {
    if(!plan||!revision)return null;
    const saved=await adPlansApi.updateRevision(projectId,plan.id,revision.id,{reviewed_concept:revision.reviewed_concept,reviewed_hook:revision.reviewed_hook,reviewed_script_sections:revision.reviewed_script_sections,reviewed_shots:revision.reviewed_shots,reviewed_prompt:revision.reviewed_prompt});setRevision(saved);return saved;
  }
  async function generate() {
    if(!plan||!revision)return; setBusy(true);setError("");
    try { const saved=await persistRevision(); if(!saved)return; const generation=await adPlansApi.generate(projectId,plan.id,saved.id);router.push(`/app/projects/${projectId}/generations/${generation.id}`); } catch(reason){setError(reason instanceof Error?reason.message:"Generation could not be started.");setBusy(false);}
  }
  async function openStudio() {
    if(!plan||!revision)return; const saved=await persistRevision(); if(!saved)return;
    sessionStorage.setItem("adsyde.planHandoff",JSON.stringify({projectId,prompt:saved.reviewed_prompt,model:form.model,aspect_ratio:form.aspect_ratio,duration_seconds:form.duration_seconds,assets:selected}));
    router.push(`/app/projects/${projectId}/create?mode=prompt`);
  }
  if(!project||!options)return <main className="page">{error?<Notice kind="error">{error}</Notice>:<Skeleton lines={7}/>}</main>;
  return <main className="page"><div className="page-head"><div><p className="eyebrow">Guided Ad Builder · Step {step} of 4</p><h1>{step===4?"Review your ad plan":"Shape the idea."}</h1></div><Link href={`/app/projects/${projectId}/create?mode=prompt`}>Use Prompt Studio</Link></div>
    {error&&<Notice kind="error">{error}</Notice>}
    {step===1&&<div className="card form-stack"><Textarea label="What are you advertising?" value={form.business_product} onChange={(event)=>setForm({...form,business_product:event.target.value})}/><Textarea label="Offer or objective" value={form.offer_objective} onChange={(event)=>setForm({...form,offer_objective:event.target.value})}/><Textarea label="Key selling points (one per line)" value={form.selling_points} onChange={(event)=>setForm({...form,selling_points:event.target.value})}/><Button disabled={busy} onClick={()=>void next()}>Save and continue</Button></div>}
    {step===2&&<div className="card form-stack"><Textarea label="Audience" value={form.audience} onChange={(event)=>setForm({...form,audience:event.target.value})}/><label className="field">Style<select value={form.style} onChange={(event)=>setForm({...form,style:event.target.value})}>{styles.map((item)=><option key={item}>{item}</option>)}</select></label><Textarea label="Custom style notes" value={form.style_notes} onChange={(event)=>setForm({...form,style_notes:event.target.value})}/><Textarea label="Call to action" value={form.call_to_action} onChange={(event)=>setForm({...form,call_to_action:event.target.value})}/><div className="top-actions"><Button variant="secondary" onClick={()=>setStep(1)}>Back</Button><Button onClick={()=>void next()}>Save and continue</Button></div></div>}
    {step===3&&<div className="card form-stack"><label className="field">Platform<select value={form.platform} onChange={(event)=>setForm({...form,platform:event.target.value,aspect_ratio:platformDefaults[event.target.value]})}>{platforms.map((item)=><option value={item} key={item}>{item.replaceAll("_"," ")}</option>)}</select></label><div className="asset-grid">{assets.map((asset)=><label className="asset-choice" key={asset.id}><input type="checkbox" checked={selected.includes(asset.id)} onChange={()=>setSelected((value)=>value.includes(asset.id)?value.filter((id)=>id!==asset.id):value.length<8?[...value,asset.id]:value)}/><PrivateImage load={()=>assetsApi.content(projectId,asset.id)} alt=""/><span>{asset.original_filename}</span></label>)}</div><div className="top-actions"><Button variant="secondary" onClick={()=>setStep(2)}>Back</Button><Button disabled={busy} onClick={()=>void makePlan()}>Generate ad plan</Button></div></div>}
    {step===4&&revision&&<div className="split"><section className="studio-main"><label className="field">Concept<textarea value={revision.reviewed_concept} onChange={(event)=>setRevision({...revision,reviewed_concept:event.target.value})}/></label><label className="field">Hook<textarea value={revision.reviewed_hook} onChange={(event)=>setRevision({...revision,reviewed_hook:event.target.value})}/></label><h2>Script</h2>{revision.reviewed_script_sections.map((section,index)=><label className="field" key={`${section.section}-${index}`}>{section.section}<textarea value={section.text} onChange={(event)=>setRevision({...revision,reviewed_script_sections:revision.reviewed_script_sections.map((item,itemIndex)=>itemIndex===index?{...item,text:event.target.value}:item)})}/></label>)}<h2>Shot plan</h2>{revision.reviewed_shots.map((shot,index)=><div className="card form-stack" key={shot.order}><strong>Shot {shot.order} · {shot.duration_ms/1000}s</strong><label className="field">Visual<textarea value={shot.visual} onChange={(event)=>setRevision({...revision,reviewed_shots:revision.reviewed_shots.map((item,itemIndex)=>itemIndex===index?{...item,visual:event.target.value}:item)})}/></label><label className="field">On-screen text<textarea value={shot.on_screen_text} onChange={(event)=>setRevision({...revision,reviewed_shots:revision.reviewed_shots.map((item,itemIndex)=>itemIndex===index?{...item,on_screen_text:event.target.value}:item)})}/></label><label className="field">Voiceover<textarea value={shot.voiceover} onChange={(event)=>setRevision({...revision,reviewed_shots:revision.reviewed_shots.map((item,itemIndex)=>itemIndex===index?{...item,voiceover:event.target.value}:item)})}/></label></div>)}<label className="field section">Final generation prompt<textarea value={revision.reviewed_prompt} onChange={(event)=>setRevision({...revision,reviewed_prompt:event.target.value})}/></label></section><aside className="studio-side"><div className="card summary"><p>{cost} credits · {wallet?.available} available</p>{short>0&&<Notice kind="error">You need {short} more credits. <Link href="/app/credits">Buy credits</Link></Notice>}<Button disabled={busy||short>0} onClick={()=>void generate()}>Generate reviewed video</Button><Button variant="secondary" onClick={()=>void openStudio()}>Open in Prompt Studio</Button><Button variant="secondary" onClick={()=>void makePlan()}>Create a new revision</Button><small>Regeneration preserves this revision and any edits.</small></div></aside></div>}
  </main>;
}

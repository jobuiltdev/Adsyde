import { GenerationDetail } from "@/components/generation-detail";
export default async function GenerationPage({params}:{params:Promise<{projectId:string;generationId:string}>}){const {projectId,generationId}=await params;return <GenerationDetail projectId={projectId} id={generationId}/>}

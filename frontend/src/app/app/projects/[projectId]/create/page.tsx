import { PromptStudio } from "@/components/prompt-studio";
export default async function CreatePage({params}:{params:Promise<{projectId:string}>}){const {projectId}=await params;return <PromptStudio projectId={projectId}/>}

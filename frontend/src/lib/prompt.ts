export type PromptMode = "exact" | "enhance";
export function effectivePrompt(prompt: string, mode: PromptMode): string {
  if (mode === "exact") return prompt;
  const normalized = prompt.trim();
  return normalized ? `${normalized}\n\nCreative direction: use a clear focal subject, deliberate pacing, and a strong final product frame.` : normalized;
}
export const isActiveStatus = (status: string) => ["queued", "submitted", "processing", "unknown"].includes(status);
export function generationMessage(status: string, code = ""): string {
  if (status === "unknown") return "We’re confirming the generation status. You don’t need to submit it again.";
  if (status === "cancelled") return "This generation was cancelled.";
  if (status === "failed") {
    if (code.includes("rejected")) return "The generation request was not accepted. Review the prompt and create a new version.";
    if (code.includes("unavailable") || code.includes("transient")) return "The generation service is temporarily unavailable. Try a new generation shortly.";
    if (code.includes("reconciliation")) return "We couldn’t confirm a final result. Your request was not automatically submitted again.";
    return "This generation could not be completed. You can return to Prompt Studio and try a revised version.";
  }
  return "Your video is moving through the generation pipeline.";
}

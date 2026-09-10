import { describe,expect,it } from "vitest";
import { effectivePrompt,generationMessage,isActiveStatus } from "./prompt";
describe("prompt behavior",()=>{
  it("preserves exact prompt bytes",()=>expect(effectivePrompt("  Keep—this!\n", "exact")).toBe("  Keep—this!\n"));
  it("adds an honest deterministic enhancement",()=>expect(effectivePrompt("Show the shoes", "enhance")).toContain("Creative direction:"));
  it("does not enhance an empty prompt",()=>expect(effectivePrompt("   ", "enhance")).toBe(""));
  it.each(["queued","submitted","processing","unknown"])("polls %s",status=>expect(isActiveStatus(status)).toBe(true));
  it.each(["completed","failed","cancelled"])("stops polling %s",status=>expect(isActiveStatus(status)).toBe(false));
  it("explains unknown without suggesting resubmission",()=>expect(generationMessage("unknown")).toContain("don’t need to submit"));
  it("distinguishes rejected failures",()=>expect(generationMessage("failed","provider_rejected")).toContain("not accepted"));
  it("explains cancellation",()=>expect(generationMessage("cancelled")).toContain("cancelled"));
});

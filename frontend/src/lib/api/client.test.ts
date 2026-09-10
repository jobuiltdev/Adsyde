import { beforeEach,describe,expect,it,vi } from "vitest";
import { ApiError,api,clearSession,errorMessage,setSession } from "./client";
describe("API client",()=>{
  beforeEach(()=>{sessionStorage.clear();clearSession();vi.restoreAllMocks()});
  it("formats structured validation errors",()=>expect(errorMessage("validation_error",{email:["Invalid email."]})).toBe("Invalid email."));
  it("uses safe throttle copy",()=>expect(errorMessage("throttled",null)).toContain("Too many"));
  it("sends the access token",async()=>{setSession({access:"access-token",refresh:"refresh-token"});const fetcher=vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response(JSON.stringify({id:"1"}),{status:200,headers:{"Content-Type":"application/json"}}));await api("/me/");expect(new Headers(fetcher.mock.calls[0][1]?.headers).get("Authorization")).toBe("Bearer access-token")});
  it("clears refresh state on logout",()=>{setSession({access:"a",refresh:"r"});clearSession();expect(sessionStorage.getItem("adsyde.refresh")).toBeNull()});
  it("throws a typed backend error",async()=>{vi.spyOn(globalThis,"fetch").mockResolvedValue(new Response(JSON.stringify({error:{code:"not_found",detail:"No."}}),{status:404}));await expect(api("/missing/")).rejects.toBeInstanceOf(ApiError)});
});

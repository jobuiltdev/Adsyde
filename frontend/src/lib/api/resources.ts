import { api, authenticatedBlob } from "./client";
import type { Asset, AssetCategory, CreditPackage, CreditTransaction, CreditWallet, Generation, GenerationOptions, Page, Payment, Project, User } from "@/lib/types";

export const authApi = {
  login: (email: string, password: string) => api<{ access: string; refresh: string }>("/auth/login/", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (email: string, password: string, password_confirm: string) => api<{ detail: string }>("/auth/register/", { method: "POST", body: JSON.stringify({ email, password, password_confirm }) }),
  verify: (uid: string, token: string) => api<{ detail: string }>("/auth/verify-email/", { method: "POST", body: JSON.stringify({ uid, token }) }),
  resend: (email: string) => api<{ detail: string }>("/auth/verification/resend/", { method: "POST", body: JSON.stringify({ email }) }),
  forgot: (email: string) => api<{ detail: string }>("/auth/password-reset/", { method: "POST", body: JSON.stringify({ email }) }),
  reset: (uid: string, token: string, new_password: string, new_password_confirm: string) => api<{ detail: string }>("/auth/password-reset/confirm/", { method: "POST", body: JSON.stringify({ uid, token, new_password, new_password_confirm }) }),
  me: () => api<User>("/me/"),
  logout: (refresh: string) => api<void>("/auth/logout/", { method: "POST", body: JSON.stringify({ refresh }) }),
};
export const projectsApi = {
  list: () => api<Page<Project>>("/projects/"),
  get: (id: string) => api<Project>(`/projects/${id}/`),
  create: (data: Pick<Project, "name" | "business_name" | "description" | "brand_style" | "target_audience">) => api<Project>("/projects/", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<Project>) => api<Project>(`/projects/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),
  remove: (id: string) => api<void>(`/projects/${id}/`, { method: "DELETE" }),
};
export const assetsApi = {
  list: (projectId: string) => api<Page<Asset>>(`/projects/${projectId}/assets/`),
  upload: (projectId: string, file: File, category: AssetCategory) => { const body = new FormData(); body.append("file", file); body.append("category", category); return api<Asset>(`/projects/${projectId}/assets/`, { method: "POST", body }); },
  remove: (projectId: string, id: string) => api<void>(`/projects/${projectId}/assets/${id}/`, { method: "DELETE" }),
  content: (projectId: string, id: string) => authenticatedBlob(`/projects/${projectId}/assets/${id}/content/`),
};
export const generationsApi = {
  options: () => api<GenerationOptions>("/generation-options/"),
  list: (projectId: string) => api<Page<Generation>>(`/projects/${projectId}/generations/`),
  get: (projectId: string, id: string) => api<Generation>(`/projects/${projectId}/generations/${id}/`),
  create: (projectId: string, data: { prompt: string; aspect_ratio: string; duration_seconds: number; model: string }) => api<Generation>(`/projects/${projectId}/generations/`, { method: "POST", body: JSON.stringify(data) }),
  cancel: (projectId: string, id: string) => api<Generation>(`/projects/${projectId}/generations/${id}/cancel/`, { method: "POST" }),
  result: (projectId: string, id: string) => authenticatedBlob(`/projects/${projectId}/generations/${id}/result/`),
};
export const creditsApi = {
  wallet: () => api<CreditWallet>("/credits/wallet/"),
  transactions: () => api<Page<CreditTransaction>>("/credits/transactions/"),
};
export const paymentsApi = {
  packages: () => api<CreditPackage[]>("/payments/packages/"),
  list: () => api<Page<Payment>>("/payments/"),
  initialize: (packageKey: string, idempotencyKey: string) => api<Payment>("/payments/initialize/", { method: "POST", headers: { "Idempotency-Key": idempotencyKey }, body: JSON.stringify({ package: packageKey }) }),
  get: (id: string) => api<Payment>(`/payments/${id}/`),
  verify: (id: string) => api<Payment>(`/payments/${id}/verify/`, { method: "POST" }),
};

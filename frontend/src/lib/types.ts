export type Page<T> = { count: number; next: string | null; previous: string | null; results: T[] };
export type User = { id: string; email: string; email_verified: boolean; date_joined: string };
export type Project = { id: string; name: string; business_name: string; description: string; brand_style: string; target_audience: string; created_at: string; updated_at: string };
export type AssetCategory = "product_image" | "logo" | "reference_image";
export type Asset = { id: string; category: AssetCategory; original_filename: string; mime_type: string; size: number; width: number; height: number; created_at: string; access_url: string };
export type GenerationStatus = "draft" | "queued" | "submitted" | "processing" | "unknown" | "completed" | "failed" | "cancelled";
export type Generation = { id: string; prompt: string; status: GenerationStatus; aspect_ratio: "9:16" | "1:1" | "16:9"; duration_seconds: number; provider_key: string; model: string; error_code: string; error_detail: string; result_available: boolean; result_url: string | null; submitted_at: string | null; started_at: string | null; completed_at: string | null; created_at: string; updated_at: string };
export type ApiErrorBody = { error?: { code?: string; detail?: unknown } };

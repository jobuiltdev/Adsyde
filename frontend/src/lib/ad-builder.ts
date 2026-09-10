import type { AssetCategory } from "./types";

export const platformDefaults: Record<string, "9:16" | "1:1" | "16:9"> = {
  tiktok: "9:16",
  instagram_reels: "9:16",
  youtube_shorts: "9:16",
  instagram_feed: "1:1",
  youtube: "16:9",
  general_social: "9:16",
};

export function roleForCategory(category: AssetCategory, selectedCount: number) {
  if (category === "logo") return "logo";
  if (category === "reference_image") return "visual_reference";
  return selectedCount === 0 ? "primary_product" : "additional_product";
}

export function shotDurationTotal(shots: Array<{ duration_ms: number }>) {
  return shots.reduce((total, shot) => total + shot.duration_ms, 0);
}

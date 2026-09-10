import { describe, expect, it } from "vitest";
import { safeGenerationSelection, validGenerationSelection } from "./generation-options";

const model = {
  key: "development-standard",
  display_name: "Standard",
  aspect_ratios: ["9:16", "1:1"] as Array<"9:16" | "1:1" | "16:9">,
  durations: [5, 10],
  supports_reference_images: false,
};

describe("generation capability selection", () => {
  it("accepts only combinations advertised by the backend", () => {
    expect(validGenerationSelection(model, "9:16", 10)).toBe(true);
    expect(validGenerationSelection(model, "16:9", 10)).toBe(false);
    expect(validGenerationSelection(model, "9:16", 20)).toBe(false);
    expect(validGenerationSelection(undefined, "9:16", 10)).toBe(false);
  });

  it("moves invalid selections to the first safe option", () => {
    expect(safeGenerationSelection(model, "16:9", 20)).toEqual({
      ratio: "9:16",
      duration: 5,
    });
  });
});

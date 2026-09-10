import { describe, expect, it } from "vitest";
import { platformDefaults, roleForCategory, shotDurationTotal } from "./ad-builder";

describe("guided ad builder", () => {
  it("uses supported platform defaults", () => {
    expect(platformDefaults.instagram_reels).toBe("9:16");
    expect(platformDefaults.youtube).toBe("16:9");
  });
  it("assigns durable asset roles", () => {
    expect(roleForCategory("logo", 0)).toBe("logo");
    expect(roleForCategory("product_image", 0)).toBe("primary_product");
    expect(roleForCategory("product_image", 1)).toBe("additional_product");
  });
  it("totals integer shot timing", () => {
    expect(shotDurationTotal([{ duration_ms: 3333 }, { duration_ms: 6667 }])).toBe(10000);
  });
});

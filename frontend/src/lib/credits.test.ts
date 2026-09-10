import { describe, expect, it } from "vitest";
import { canAffordGeneration, creditActivityAmount, creditShortfall } from "./credits";
import { errorMessage } from "./api/client";

describe("credit presentation", () => {
  it("calculates insufficient-credit states", () => {
    expect(creditShortfall(80, 120)).toBe(40);
    expect(creditShortfall(120, 120)).toBe(0);
  });

  it("disables generation until wallet and quote are available", () => {
    expect(canAffordGeneration(undefined, 120)).toBe(false);
    expect(canAffordGeneration(500, undefined)).toBe(false);
    expect(canAffordGeneration(119, 120)).toBe(false);
    expect(canAffordGeneration(120, 120)).toBe(true);
  });

  it("renders balance or reservation movement", () => {
    expect(creditActivityAmount(-120, -120)).toBe(-120);
    expect(creditActivityAmount(0, 120)).toBe(120);
  });

  it("handles the backend insufficient-credit error safely", () => {
    expect(errorMessage("INSUFFICIENT_CREDITS", { required: 120 })).toContain(
      "enough available credits",
    );
  });
});

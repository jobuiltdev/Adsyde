import { describe, expect, it } from "vitest";
import { formatNgn, paymentIsPending, safeCheckoutUrl } from "./payments";

describe("payment presentation", () => {
  it("formats integer kobo as NGN", () => {
    expect(formatNgn(500000)).toContain("5,000");
  });
  it("only accepts the checkout host", () => {
    expect(safeCheckoutUrl("https://checkout.paystack.com/test")).toBe(true);
    expect(safeCheckoutUrl("https://example.com/test")).toBe(false);
    expect(safeCheckoutUrl("javascript:alert(1)")).toBe(false);
  });
  it("keeps uncertain states pending", () => {
    expect(paymentIsPending("verification_required")).toBe(true);
    expect(paymentIsPending("succeeded")).toBe(false);
  });
});

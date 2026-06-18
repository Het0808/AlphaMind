import { describe, it, expect } from "vitest";
import {
  formatINRCrore, formatINRIntl, formatMoney, formatUSD, nativeSymbol, toINR,
} from "./currency-format";

describe("Indian notation (₹ Cr / L Cr)", () => {
  it("matches the required example formats", () => {
    expect(formatINRCrore(1.25e7)).toBe("₹1.25 Cr");
    expect(formatINRCrore(5e9)).toBe("₹500 Cr");
    expect(formatINRCrore(1.25e11)).toBe("₹12.5K Cr");
    expect(formatINRCrore(2.3e12)).toBe("₹2.3 L Cr");
  });
});

describe("US notation: original USD + converted INR", () => {
  it("renders '$3.2T (₹274T)'", () => {
    // 3.2T × 85.625 = 274T exactly
    expect(formatMoney(3.2e12, "USD", 85.625)).toBe("$3.2T (₹274T)");
  });
});

// ── Per-company verification (Apple, Microsoft, Nvidia, Infosys, Reliance) ──
const RATE = 85.5;

describe("Apple (USD)", () => {
  const marketCap = 3.4e12;
  it("shows USD then converted INR", () => {
    const s = formatMoney(marketCap, "USD", RATE);
    expect(s.startsWith("$3.4T")).toBe(true);
    expect(s).toContain("₹");
    expect(s).toContain("T)");
    expect(nativeSymbol("USD")).toBe("$");
  });
});

describe("Microsoft (USD)", () => {
  it("converts revenue to INR", () => {
    expect(formatMoney(2.817e11, "USD", RATE)).toBe(`${formatUSD(2.817e11)} (${formatINRIntl(2.817e11 * RATE)})`);
    expect(formatMoney(2.817e11, "USD", RATE)).toContain("$281.7B");
  });
});

describe("Nvidia (USD)", () => {
  it("market cap shows both currencies", () => {
    const s = formatMoney(3.1e12, "USD", RATE);
    expect(s).toContain("$3.1T");
    expect(s).toContain("₹");
  });
});

describe("Infosys (INR-native)", () => {
  it("uses Indian crore notation, no USD", () => {
    const s = formatMoney(6.6e12, "INR", RATE); // ~₹6.6 lakh crore
    expect(s).toBe("₹6.6 L Cr");
    expect(s).not.toContain("$");
    expect(nativeSymbol("INR")).toBe("₹");
    expect(toINR(6.6e12, "INR", RATE)).toBe(6.6e12); // identity for INR
  });
});

describe("Reliance (INR-native)", () => {
  it("formats large INR market cap", () => {
    expect(formatMoney(1.9e13, "INR", RATE)).toBe("₹19 L Cr");
    expect(formatMoney(5e9, "INR", RATE)).toBe("₹500 Cr");
  });
});

describe("non-monetary values are NOT routed through formatMoney", () => {
  it("toINR converts USD but leaves INR identity", () => {
    expect(toINR(100, "USD", 85.5)).toBe(8550);
    expect(toINR(100, "INR", 85.5)).toBe(100);
  });
  it("null/NaN are safe", () => {
    expect(formatMoney(null, "USD", RATE)).toBe("—");
    expect(formatMoney(undefined, "INR", RATE)).toBe("—");
  });
});

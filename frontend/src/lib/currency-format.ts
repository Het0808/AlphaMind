// Pure currency formatters (no React / no storage) — unit-testable.
//
// Indian stocks (INR-native): Indian notation → ₹1.25 Cr · ₹500 Cr · ₹12.5K Cr · ₹2.3 L Cr
// US stocks (USD-native): original USD + converted INR → "$3.2T (₹274T)"
//
// Only MONETARY magnitudes are converted. Ratios/per-share (EPS, P/E, ROE,
// margins, growth) must NOT pass through here.

export const DEFAULT_USD_INR = 85.5;

// Trim trailing zeros: 500.00 → "500", 12.50 → "12.5", 1.25 → "1.25".
const n = (v: number) => parseFloat(v.toFixed(2)).toString();

export function formatUSD(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  const a = Math.abs(value), s = value < 0 ? "-" : "";
  if (a >= 1e12) return `${s}$${n(a / 1e12)}T`;
  if (a >= 1e9) return `${s}$${n(a / 1e9)}B`;
  if (a >= 1e6) return `${s}$${n(a / 1e6)}M`;
  if (a >= 1e3) return `${s}$${n(a / 1e3)}K`;
  return `${s}$${n(a)}`;
}

/** International ₹ notation (T/B/M/K) — used for INR-converted US values. */
export function formatINRIntl(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  const a = Math.abs(value), s = value < 0 ? "-" : "";
  if (a >= 1e12) return `${s}₹${n(a / 1e12)}T`;
  if (a >= 1e9) return `${s}₹${n(a / 1e9)}B`;
  if (a >= 1e6) return `${s}₹${n(a / 1e6)}M`;
  if (a >= 1e3) return `${s}₹${n(a / 1e3)}K`;
  return `${s}₹${n(a)}`;
}

/** Indian notation (Crore / Lakh) — used for INR-native Indian values. */
export function formatINRCrore(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  const a = Math.abs(value), s = value < 0 ? "-" : "";
  if (a >= 1e12) return `${s}₹${n(a / 1e12)} L Cr`;   // lakh crore
  if (a >= 1e10) return `${s}₹${n(a / 1e10)}K Cr`;    // thousand crore
  if (a >= 1e7) return `${s}₹${n(a / 1e7)} Cr`;       // crore
  if (a >= 1e5) return `${s}₹${n(a / 1e5)} L`;        // lakh
  if (a >= 1e3) return `${s}₹${n(a / 1e3)}K`;
  return `${s}₹${n(a)}`;
}

/**
 * Format a monetary value for display.
 * - INR-native  → Indian crore notation, e.g. "₹2.3 L Cr"
 * - USD-native  → "$3.2T (₹274T)" (original + converted)
 */
export function formatMoney(value: number | null | undefined, currency: string | undefined, rate: number = DEFAULT_USD_INR): string {
  if (value == null || Number.isNaN(value)) return "—";
  if ((currency ?? "USD").toUpperCase() === "INR") return formatINRCrore(value);
  return `${formatUSD(value)} (${formatINRIntl(value * rate)})`;
}

/** Native symbol for non-converted figures (EPS etc.). */
export const nativeSymbol = (currency?: string) => ((currency ?? "USD").toUpperCase() === "INR" ? "₹" : "$");

/** Convert any value to INR (identity if already INR). */
export const toINR = (value: number, currency: string | undefined, rate: number) =>
  ((currency ?? "USD").toUpperCase() === "INR" ? value : value * rate);

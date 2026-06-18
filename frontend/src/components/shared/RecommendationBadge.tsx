import { Badge } from "@/components/ui/badge";
import type { Recommendation } from "@/lib/types";

const MAP: Record<Recommendation, { variant: "bull" | "bear" | "warn"; label: string }> = {
  STRONG_BUY: { variant: "bull", label: "Strong Buy" },
  BUY: { variant: "bull", label: "Buy" },
  HOLD: { variant: "warn", label: "Hold" },
  SELL: { variant: "bear", label: "Sell" },
  STRONG_SELL: { variant: "bear", label: "Strong Sell" },
};

export function RecommendationBadge({ value }: { value: Recommendation }) {
  const m = MAP[value] ?? MAP.HOLD;
  return <Badge variant={m.variant}>{m.label}</Badge>;
}

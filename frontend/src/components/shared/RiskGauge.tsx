import { cn } from "@/lib/utils";
import type { RiskLevel } from "@/lib/types";

const LEVEL_TONE: Record<RiskLevel, string> = {
  LOW: "text-bull",
  MODERATE: "text-warn",
  ELEVATED: "text-accent",
  HIGH: "text-bear",
};

/** Risk score 1–10 + qualitative level, rendered as a radial-style gauge. */
export function RiskGauge({ score, level, className }: { score: number; level: RiskLevel; className?: string }) {
  const v = Math.max(0, Math.min(10, score));
  const pct = (v / 10) * 100;
  const tone = v >= 7 ? "hsl(var(--bear))" : v >= 5 ? "hsl(var(--warn))" : "hsl(var(--bull))";
  return (
    <div className={cn("flex items-center gap-4", className)}>
      <div
        className="relative grid h-20 w-20 place-items-center rounded-full"
        style={{ background: `conic-gradient(${tone} ${pct}%, hsl(var(--muted)) ${pct}%)` }}
      >
        <div className="grid h-[60px] w-[60px] place-items-center rounded-full bg-card">
          <span className="mono text-lg font-bold">{v}</span>
        </div>
      </div>
      <div>
        <div className="label">Risk level</div>
        <div className={cn("text-base font-semibold", LEVEL_TONE[level])}>{level}</div>
        <div className="mono text-xs text-muted-foreground">{v}/10 composite</div>
      </div>
    </div>
  );
}

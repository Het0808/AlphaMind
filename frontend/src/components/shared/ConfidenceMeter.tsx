import { cn } from "@/lib/utils";

/** 1–10 confidence shown as a segmented terminal-style meter. */
export function ConfidenceMeter({ value, label = "Confidence", className }: { value: number; label?: string; className?: string }) {
  const v = Math.max(0, Math.min(10, value));
  const tone = v >= 7 ? "bg-bull" : v >= 5 ? "bg-warn" : "bg-bear";
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <div className="flex items-center justify-between">
        <span className="label">{label}</span>
        <span className="mono text-sm font-semibold">{v}/10</span>
      </div>
      <div className="flex gap-1">
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className={cn("h-2 flex-1 rounded-sm", i < v ? tone : "bg-muted")} />
        ))}
      </div>
    </div>
  );
}

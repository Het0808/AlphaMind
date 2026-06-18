import { cn } from "@/lib/utils";

export function StatCard({
  label, value, sub, tone = "default", className,
}: {
  label: string;
  value: React.ReactNode;
  sub?: React.ReactNode;
  tone?: "default" | "up" | "down" | "warn";
  className?: string;
}) {
  const toneClass =
    tone === "up" ? "text-bull" : tone === "down" ? "text-bear" : tone === "warn" ? "text-warn" : "text-foreground";
  return (
    <div className={cn("panel panel-pad", className)}>
      <div className="label">{label}</div>
      <div className={cn("mono mt-1 text-xl font-semibold", toneClass)}>{value}</div>
      {sub != null && <div className="mt-0.5 text-xs text-muted-foreground">{sub}</div>}
    </div>
  );
}

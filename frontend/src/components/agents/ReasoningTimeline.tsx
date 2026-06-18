import { CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface Step { agent: string; detail: string; }

/** Vertical timeline of the agent pipeline — a clean "OpenAI" reasoning view. */
export function ReasoningTimeline({ steps }: { steps: Step[] }) {
  return (
    <ol className="relative ml-3 border-l border-border">
      {steps.map((s, i) => (
        <li key={i} className="mb-5 ml-5 animate-fade-in" style={{ animationDelay: `${i * 60}ms` }}>
          <span className="absolute -left-[9px] grid h-4 w-4 place-items-center rounded-full bg-card ring-1 ring-border">
            <CheckCircle2 className="h-3.5 w-3.5 text-primary" />
          </span>
          <div className={cn("text-xs font-semibold uppercase tracking-wider text-primary")}>{s.agent}</div>
          <div className="text-sm text-foreground/80">{s.detail}</div>
        </li>
      ))}
    </ol>
  );
}

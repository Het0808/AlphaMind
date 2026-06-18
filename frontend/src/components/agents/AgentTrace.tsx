import { cn } from "@/lib/utils";

const AGENT_TONE: Record<string, string> = {
  supervisor: "text-accent",
  research: "text-info",
  financial: "text-primary",
  news: "text-foreground",
  risk: "text-bear",
  bull: "text-bull",
  bear: "text-bear",
  judge: "text-accent",
};

/** Terminal-style streaming log of agent thoughts (the graph trace). */
export function AgentTrace({ trace, className }: { trace: string[]; className?: string }) {
  return (
    <div className={cn("scroll-thin max-h-[320px] overflow-auto rounded-md bg-background/60 p-3 font-mono text-xs", className)}>
      {trace.map((line, i) => {
        const [agent, ...rest] = line.split(":");
        const tone = AGENT_TONE[agent.trim().split(" ")[0]] ?? "text-muted-foreground";
        return (
          <div key={i} className="flex gap-2 py-0.5 leading-relaxed animate-fade-in">
            <span className="select-none text-muted-foreground">{String(i + 1).padStart(2, "0")}</span>
            <span className={cn("font-semibold", tone)}>{agent}</span>
            <span className="text-foreground/80">{rest.join(":")}</span>
          </div>
        );
      })}
    </div>
  );
}

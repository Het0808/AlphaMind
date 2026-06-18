import { cn } from "@/lib/utils";

export type AgentState = "idle" | "running" | "done" | "error";

const TONE: Record<AgentState, string> = {
  idle: "bg-muted-foreground/40",
  running: "bg-warn glow-warn animate-pulse",
  done: "bg-bull glow-bull",
  error: "bg-bear",
};

/** A horizontal rail of agent pipeline status indicators. */
export function AgentStatusBar({
  agents, state, className,
}: { agents: string[]; state: AgentState; className?: string }) {
  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {agents.map((name) => (
        <div
          key={name}
          className="flex items-center gap-2 rounded-full border border-border/70 bg-card/50 px-2.5 py-1 backdrop-blur"
        >
          <span className={cn("h-2 w-2 rounded-full transition-colors", TONE[state])} />
          <span className="text-[11px] font-medium text-foreground/80">{name}</span>
        </div>
      ))}
    </div>
  );
}

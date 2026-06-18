import { SearchX } from "lucide-react";

export function EmptyState({ title = "No company selected", hint = "Search a ticker or company name to begin." }: { title?: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border/70 bg-card/30 py-20 text-center">
      <div className="grid h-12 w-12 place-items-center rounded-full bg-muted/60">
        <SearchX className="h-6 w-6 text-muted-foreground" />
      </div>
      <div>
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs text-muted-foreground">{hint}</p>
      </div>
    </div>
  );
}

import { ExternalLink, FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { Citation } from "@/lib/types";

export function CitationList({ citations }: { citations: Citation[] }) {
  if (!citations.length) {
    return <p className="text-xs text-muted-foreground">No filing citations available.</p>;
  }
  return (
    <ul className="space-y-2">
      {citations.map((c, i) => (
        <li key={i} className="panel panel-pad animate-fade-in">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-info" />
              <Badge variant="info">{c.form}</Badge>
              <span className="text-xs font-medium">{c.section}</span>
            </div>
            {typeof c.score === "number" && (
              <span className="mono text-[10px] text-muted-foreground">sim {c.score.toFixed(2)}</span>
            )}
          </div>
          {c.snippet && <p className="mt-1.5 line-clamp-2 text-xs text-foreground/70">“{c.snippet}”</p>}
          <div className="mt-2 flex items-center justify-between">
            <span className="mono text-[10px] text-muted-foreground">
              {c.ticker} · filed {c.filing_date} · acc {c.accession}
            </span>
            <a
              href={c.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[10px] font-medium text-primary hover:underline"
            >
              SEC <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        </li>
      ))}
    </ul>
  );
}

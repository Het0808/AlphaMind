import { Scale } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ConfidenceMeter } from "@/components/shared/ConfidenceMeter";
import { RecommendationBadge } from "@/components/shared/RecommendationBadge";
import { cn } from "@/lib/utils";
import type { DebateResult } from "@/lib/types";

export function DebatePanel({ debate }: { debate: DebateResult }) {
  return (
    <div className="space-y-4">
      {/* Bull vs Bear theses */}
      <div className="grid gap-4 md:grid-cols-2">
        <SideCard stance="bull" thesis={debate.bull_thesis} />
        <SideCard stance="bear" thesis={debate.bear_thesis} />
      </div>

      {/* Judge */}
      <Card className="border-accent/30">
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Scale className="h-4 w-4 text-accent" /> Judge Decision
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={debate.judge.winner === "bull" ? "bull" : debate.judge.winner === "bear" ? "bear" : "warn"}>
              {debate.judge.winner} wins
            </Badge>
            <RecommendationBadge value={debate.judge.recommendation} />
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <p className="text-sm text-foreground/85">{debate.judge.reasoning}</p>
          <div className="grid gap-3 sm:grid-cols-3">
            <ScoreBar label="Bull score" value={debate.judge.bull_score} tone="bull" />
            <ScoreBar label="Bear score" value={debate.judge.bear_score} tone="bear" />
            <ConfidenceMeter value={debate.judge.confidence} label="Verdict confidence" />
          </div>
          <div className="rounded-md bg-muted/50 p-3 text-xs">
            <span className="label">Decisive argument</span>
            <p className="mt-1 text-foreground/85">{debate.judge.decisive_argument}</p>
          </div>
        </CardContent>
      </Card>

      {/* Round-by-round transcript (debate history) */}
      <Card>
        <CardHeader><CardTitle>Debate History — {debate.rounds} rounds</CardTitle></CardHeader>
        <CardContent className="space-y-2">
          {debate.transcript.map((turn, i) => (
            <div
              key={i}
              className={cn(
                "rounded-md border-l-2 bg-muted/30 p-3",
                turn.stance === "bull" ? "border-l-bull" : "border-l-bear",
              )}
            >
              <div className="mb-1 flex items-center justify-between">
                <Badge variant={turn.stance === "bull" ? "bull" : "bear"}>
                  Round {turn.round} · {turn.stance}
                </Badge>
                <span className="mono text-xs text-muted-foreground">conf {turn.confidence}/10</span>
              </div>
              <p className="text-sm font-medium">{turn.summary}</p>
              <ul className="mt-1 list-inside list-disc text-xs text-foreground/75">
                {turn.claims.map((c, j) => <li key={j}>{c}</li>)}
              </ul>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

function SideCard({ stance, thesis }: { stance: "bull" | "bear"; thesis: DebateResult["bull_thesis"] }) {
  return (
    <Card className={cn(stance === "bull" ? "border-bull/30" : "border-bear/30")}>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle className={stance === "bull" ? "text-bull" : "text-bear"}>
          {stance === "bull" ? "🐂 Bull Thesis" : "🐻 Bear Thesis"}
        </CardTitle>
        <span className="mono text-xs text-muted-foreground">conf {thesis.confidence}/10</span>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="text-sm text-foreground/85">{thesis.thesis}</p>
        <div>
          <span className="label">Key points</span>
          <ul className="mt-1 list-inside list-disc text-xs text-foreground/75">
            {thesis.key_points.map((p, i) => <li key={i}>{p}</li>)}
          </ul>
        </div>
        <div className="rounded-md bg-muted/40 p-2 text-xs">
          <span className="label">Strongest point</span>
          <p className="mt-0.5 text-foreground/85">{thesis.strongest_point}</p>
        </div>
      </CardContent>
    </Card>
  );
}

function ScoreBar({ label, value, tone }: { label: string; value: number; tone: "bull" | "bear" }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center justify-between">
        <span className="label">{label}</span>
        <span className="mono text-sm font-semibold">{value}/10</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={cn("h-full rounded-full", tone === "bull" ? "bg-bull" : "bg-bear")}
          style={{ width: `${value * 10}%` }}
        />
      </div>
    </div>
  );
}

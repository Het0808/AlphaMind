"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { SectionHeading } from "@/components/shared/SectionHeading";
import { TickerInput } from "@/components/shared/TickerInput";
import { StatCard } from "@/components/shared/StatCard";
import { RecommendationBadge } from "@/components/shared/RecommendationBadge";
import { ConfidenceMeter } from "@/components/shared/ConfidenceMeter";
import { RiskGauge } from "@/components/shared/RiskGauge";
import { AgentTrace } from "@/components/agents/AgentTrace";
import { AgentStatusBar } from "@/components/shared/AgentStatus";
import { CitationList } from "@/components/citations/CitationList";
import { EmptyState } from "@/components/shared/EmptyState";
import { useCompanyStore } from "@/lib/store";
import { mockCitationsFor } from "@/lib/mock";

export default function ResearchWorkspace() {
  const report = useCompanyStore((s) => s.analysisData);
  const loading = useCompanyStore((s) => s.loading);
  const selectedTicker = useCompanyStore((s) => s.selectedTicker);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <SectionHeading
        title="Research Workspace"
        subtitle="Run the full multi-agent pipeline and review the synthesized thesis"
        right={<TickerInput />}
      />

      <AgentStatusBar
        agents={["Supervisor", "Research", "Financial", "News", "Risk", "Synthesis"]}
        state={loading ? "running" : report ? "done" : "idle"}
      />

      {loading || (!report && selectedTicker) ? (
        <LoadingState />
      ) : !report ? (
        <EmptyState />
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
            <Card>
              <CardHeader className="flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-base">
                    {report.company_name} <span className="mono text-muted-foreground">· {report.ticker}</span>
                  </CardTitle>
                  <p className="text-xs text-muted-foreground">{report.research.sector} · {report.horizon} horizon</p>
                </div>
                <RecommendationBadge value={report.recommendation} />
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-sm text-foreground/85">{report.executive_summary}</p>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <span className="label">Thesis</span>
                    <ul className="mt-1 list-inside list-disc space-y-1 text-xs text-foreground/80">
                      {report.key_thesis.map((t, i) => <li key={i}>{t}</li>)}
                    </ul>
                  </div>
                  <div>
                    <span className="label">Key risks</span>
                    <ul className="mt-1 list-inside list-disc space-y-1 text-xs text-foreground/80">
                      {report.key_risks.map((t, i) => <li key={i}>{t}</li>)}
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardContent className="space-y-4 pt-4">
                <ConfidenceMeter value={report.conviction} label="Conviction" />
                <RiskGauge score={report.risk.risk_score} level={report.risk.overall_risk} />
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 sm:grid-cols-4">
            <StatCard label="Recommendation" value={report.recommendation.replace("_", " ")} tone={report.recommendation.includes("BUY") ? "up" : report.recommendation.includes("SELL") ? "down" : "warn"} />
            <StatCard label="Conviction" value={`${report.conviction}/10`} />
            <StatCard label="Risk score" value={`${report.risk.risk_score}/10`} tone="warn" />
            <StatCard label="Fin. health" value={`${report.financials.financial_health_score}/10`} tone="up" />
          </div>

          <Tabs defaultValue="research">
            <TabsList>
              <TabsTrigger value="research">Research</TabsTrigger>
              <TabsTrigger value="trace">Agent Thoughts</TabsTrigger>
              <TabsTrigger value="citations">Citations</TabsTrigger>
              <TabsTrigger value="news">News</TabsTrigger>
            </TabsList>

            <TabsContent value="research">
              <div className="grid gap-4 md:grid-cols-2">
                <Card><CardHeader><CardTitle className="text-bull">Bull case</CardTitle></CardHeader>
                  <CardContent className="text-sm text-foreground/85">{report.research.bull_case}</CardContent></Card>
                <Card><CardHeader><CardTitle className="text-bear">Bear case</CardTitle></CardHeader>
                  <CardContent className="text-sm text-foreground/85">{report.research.bear_case}</CardContent></Card>
              </div>
            </TabsContent>

            <TabsContent value="trace">
              <Card><CardHeader><CardTitle>Agent execution trace</CardTitle></CardHeader>
                <CardContent><AgentTrace trace={report.trace} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="citations">
              <Card><CardHeader><CardTitle>SEC filing citations</CardTitle></CardHeader>
                <CardContent><CitationList citations={mockCitationsFor(report.ticker)} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="news">
              <Card>
                <CardHeader className="flex-row items-center justify-between">
                  <CardTitle>News & sentiment</CardTitle>
                  <Badge variant="info">{report.news.overall_sentiment}</Badge>
                </CardHeader>
                <CardContent className="space-y-2">
                  <p className="text-sm text-foreground/85">{report.news.summary}</p>
                  {report.news.notable_items.map((n, i) => (
                    <div key={i} className="rounded-md bg-muted/30 p-2 text-xs">
                      <span className="font-medium">{n.headline}</span>
                      <span className="ml-2 text-muted-foreground">— {n.relevance}</span>
                    </div>
                  ))}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-48 w-full" />
      <div className="grid gap-4 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-20" />)}
      </div>
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

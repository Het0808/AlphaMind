"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SectionHeading } from "@/components/shared/SectionHeading";
import { TickerInput } from "@/components/shared/TickerInput";
import { AgentTrace } from "@/components/agents/AgentTrace";
import { ReasoningTimeline } from "@/components/agents/ReasoningTimeline";
import { DebatePanel } from "@/components/agents/DebatePanel";
import { EmptyState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { useCompanyStore } from "@/lib/store";

const PIPELINE = [
  { agent: "Supervisor", detail: "Plans the analysis and dispatches specialists." },
  { agent: "Research", detail: "Builds the qualitative thesis, grounded in SEC filings." },
  { agent: "Financial", detail: "Interprets fundamentals from Yahoo / EDGAR / FMP." },
  { agent: "News", detail: "Assesses sentiment and catalysts." },
  { agent: "Risk", detail: "Scores market, financial and business risk." },
  { agent: "Supervisor", detail: "Synthesizes the final recommendation + conviction." },
];

export default function AgentReasoning() {
  const report = useCompanyStore((s) => s.analysisData);
  const debate = useCompanyStore((s) => s.debateData);
  const loading = useCompanyStore((s) => s.loading);
  const selectedTicker = useCompanyStore((s) => s.selectedTicker);
  const company = useCompanyStore((s) => s.selectedCompany);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <SectionHeading
        title="Agent Reasoning Viewer"
        subtitle={company ? `Inspecting ${company} (${selectedTicker})` : "Inspect agent thoughts, the reasoning pipeline, and the debate"}
        right={<TickerInput />}
      />

      {loading || (selectedTicker && (!report || !debate)) ? (
        <Skeleton className="h-96 w-full" />
      ) : !report || !debate ? (
        <EmptyState />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
          <Card className="h-fit">
            <CardHeader><CardTitle>Reasoning pipeline</CardTitle></CardHeader>
            <CardContent><ReasoningTimeline steps={PIPELINE} /></CardContent>
          </Card>

          <Tabs defaultValue="thoughts">
            <TabsList>
              <TabsTrigger value="thoughts">Agent Thoughts</TabsTrigger>
              <TabsTrigger value="debate">Debate History</TabsTrigger>
            </TabsList>
            <TabsContent value="thoughts">
              <Card>
                <CardHeader><CardTitle>Live agent trace · {report.ticker}</CardTitle></CardHeader>
                <CardContent><AgentTrace trace={report.trace} /></CardContent>
              </Card>
            </TabsContent>
            <TabsContent value="debate">
              <DebatePanel debate={debate} />
            </TabsContent>
          </Tabs>
        </div>
      )}
    </div>
  );
}

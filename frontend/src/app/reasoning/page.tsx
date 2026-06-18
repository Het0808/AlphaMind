"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SectionHeading } from "@/components/shared/SectionHeading";
import { TickerInput } from "@/components/shared/TickerInput";
import { AgentTrace } from "@/components/agents/AgentTrace";
import { ReasoningTimeline } from "@/components/agents/ReasoningTimeline";
import { DebatePanel } from "@/components/agents/DebatePanel";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { DEFAULT_TICKER } from "@/lib/constants";
import type { DebateResult, InvestmentReport } from "@/lib/types";

const PIPELINE = [
  { agent: "Supervisor", detail: "Plans the analysis and dispatches specialists." },
  { agent: "Research", detail: "Builds the qualitative thesis, grounded in SEC filings." },
  { agent: "Financial", detail: "Interprets fundamentals from Yahoo / EDGAR / FMP." },
  { agent: "News", detail: "Assesses sentiment and catalysts." },
  { agent: "Risk", detail: "Scores market, financial and business risk." },
  { agent: "Supervisor", detail: "Synthesizes the final recommendation + conviction." },
];

export default function AgentReasoning() {
  const [report, setReport] = React.useState<InvestmentReport | null>(null);
  const [debate, setDebate] = React.useState<DebateResult | null>(null);
  const [loading, setLoading] = React.useState(true);

  const run = React.useCallback(async (ticker: string) => {
    setLoading(true);
    const [r, d] = await Promise.all([api.analyze(ticker), api.debate(ticker)]);
    setReport(r.data); setDebate(d.data);
    setLoading(false);
  }, []);

  React.useEffect(() => { run(DEFAULT_TICKER); }, [run]);

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <SectionHeading
        title="Agent Reasoning Viewer"
        subtitle="Inspect agent thoughts, the reasoning pipeline, and the debate"
        right={<TickerInput loading={loading} onSubmit={run} />}
      />

      {loading || !report || !debate ? (
        <Skeleton className="h-96 w-full" />
      ) : (
        <div className="grid gap-4 lg:grid-cols-[1fr_1.4fr]">
          <Card className="h-fit">
            <CardHeader><CardTitle>Reasoning pipeline</CardTitle></CardHeader>
            <CardContent><ReasoningTimeline steps={PIPELINE} /></CardContent>
          </Card>

          <div className="space-y-4">
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
        </div>
      )}
    </div>
  );
}

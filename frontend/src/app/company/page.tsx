"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SectionHeading } from "@/components/shared/SectionHeading";
import { TickerInput } from "@/components/shared/TickerInput";
import { StatCard } from "@/components/shared/StatCard";
import { RecommendationBadge } from "@/components/shared/RecommendationBadge";
import { RiskGauge } from "@/components/shared/RiskGauge";
import { DebatePanel } from "@/components/agents/DebatePanel";
import { CitationList } from "@/components/citations/CitationList";
import { EmptyState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { useCompanyStore } from "@/lib/store";
import { mockCitationsFor } from "@/lib/mock";
import { fmtCurrency, fmtNumber } from "@/lib/utils";

export default function CompanyAnalysis() {
  const report = useCompanyStore((s) => s.analysisData);
  const snap = useCompanyStore((s) => s.financialData);
  const debate = useCompanyStore((s) => s.debateData);
  const loading = useCompanyStore((s) => s.loading);
  const selectedTicker = useCompanyStore((s) => s.selectedTicker);

  const header = (
    <SectionHeading
      title="Company Analysis"
      subtitle="Deep-dive: fundamentals, thesis, debate and citations"
      right={<TickerInput />}
    />
  );

  if (loading || (selectedTicker && (!report || !snap || !debate))) {
    return (
      <div className="mx-auto max-w-7xl space-y-4">
        {header}
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-72 w-full" />
      </div>
    );
  }
  if (!report || !snap || !debate) {
    return <div className="mx-auto max-w-7xl space-y-4">{header}<EmptyState /></div>;
  }

  const m = snap.metrics;

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      {header}

      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-4">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-semibold">{snap.overview.name}</h2>
              <Badge variant="secondary" className="mono">{snap.ticker}</Badge>
              <RecommendationBadge value={report.recommendation} />
            </div>
            <p className="text-xs text-muted-foreground">
              {snap.overview.sector} · {snap.overview.industry} · {snap.overview.exchange} · {fmtNumber(snap.overview.employees, 0)} employees
            </p>
          </div>
          <RiskGauge score={report.risk.risk_score} level={report.risk.overall_risk} />
        </CardContent>
      </Card>

      <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Market cap" value={fmtCurrency(m.market_cap)} />
        <StatCard label="Revenue" value={fmtCurrency(m.revenue)} tone="up" />
        <StatCard label="Net income" value={fmtCurrency(m.net_income)} tone="up" />
        <StatCard label="EPS" value={fmtNumber(m.eps)} />
        <StatCard label="P/E" value={fmtNumber(m.pe_ratio)} tone="warn" />
        <StatCard label="Free cash flow" value={fmtCurrency(m.free_cash_flow)} tone="up" />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Business & moat</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm text-foreground/85">
            <p>{report.research.business_summary}</p>
            <div><span className="label">Economic moat</span><p className="mt-0.5">{report.research.moat}</p></div>
            <div className="flex flex-wrap gap-1.5 pt-1">
              {report.research.growth_drivers.map((g, i) => <Badge key={i} variant="bull">{g}</Badge>)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Financial read</CardTitle></CardHeader>
          <CardContent className="space-y-2 text-sm text-foreground/85">
            <p><span className="label">Valuation</span><br />{report.financials.valuation_summary}</p>
            <p><span className="label">Profitability</span><br />{report.financials.profitability}</p>
            <p className="text-xs text-muted-foreground">Sources: {snap.providers_used.join(", ")}</p>
          </CardContent>
        </Card>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold">Bull / Bear / Judge debate</h3>
        <DebatePanel debate={debate} />
      </div>

      <Card>
        <CardHeader><CardTitle>Primary-source citations</CardTitle></CardHeader>
        <CardContent><CitationList citations={mockCitationsFor(snap.ticker)} /></CardContent>
      </Card>
    </div>
  );
}

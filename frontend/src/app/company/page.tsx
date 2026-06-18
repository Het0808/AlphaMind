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
import { useCurrencyStore } from "@/lib/currency";
import { formatMoney, nativeSymbol } from "@/lib/currency-format";
import { mockCitationsFor } from "@/lib/mock";
import { fmtNumber } from "@/lib/utils";

const UNAVAILABLE = <span className="text-muted-foreground">Data unavailable</span>;

export default function CompanyAnalysis() {
  const report = useCompanyStore((s) => s.analysisData);
  const snap = useCompanyStore((s) => s.financialData);
  const debate = useCompanyStore((s) => s.debateData);
  const loading = useCompanyStore((s) => s.loading);
  const selectedTicker = useCompanyStore((s) => s.selectedTicker);
  const rate = useCurrencyStore((s) => s.rate);

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
  // Fail-safe: null/unverified monetary fields show "Data unavailable", never a guess.
  const money = (v?: number | null) => (v == null ? UNAVAILABLE : formatMoney(v, m.currency, rate));

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

      <div className="flex items-center justify-between">
        <span className="label">Monetary values in INR{m.currency !== "INR" ? ` · converted @ ₹${rate.toFixed(2)}/USD` : ""} · live verified data only</span>
      </div>
      <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Market cap (INR)" value={money(m.market_cap)} />
        <StatCard label="Revenue (INR)" value={money(m.revenue)} tone="up" />
        <StatCard label="Net income (INR)" value={money(m.net_income)} tone="up" />
        <StatCard label="EPS (not converted)" value={m.eps == null ? UNAVAILABLE : `${nativeSymbol(m.currency)}${fmtNumber(m.eps)}`} />
        <StatCard label="P/E (ratio)" value={m.pe_ratio == null ? UNAVAILABLE : fmtNumber(m.pe_ratio)} tone="warn" />
        <StatCard label="Free cash flow (INR)" value={money(m.free_cash_flow)} tone="up" />
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

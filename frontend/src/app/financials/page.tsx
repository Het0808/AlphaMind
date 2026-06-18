"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SectionHeading } from "@/components/shared/SectionHeading";
import { TickerInput } from "@/components/shared/TickerInput";
import { StatCard } from "@/components/shared/StatCard";
import { PriceArea, MetricBars, RiskRadar } from "@/components/charts/Charts";
import { EmptyState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { useCompanyStore } from "@/lib/store";
import { mockPriceSeriesFor } from "@/lib/mock";
import { fmtCurrency, fmtNumber } from "@/lib/utils";

export default function FinancialDashboard() {
  const snap = useCompanyStore((s) => s.financialData);
  const report = useCompanyStore((s) => s.analysisData);
  const loading = useCompanyStore((s) => s.loading);
  const selectedTicker = useCompanyStore((s) => s.selectedTicker);

  const header = (
    <SectionHeading
      title="Financial Dashboard"
      subtitle={snap ? `${snap.overview.name} · ${snap.metrics.fiscal_period}` : "Charts, fundamentals and risk decomposition"}
      right={<TickerInput />}
    />
  );

  if (loading || (selectedTicker && (!snap || !report))) {
    return <div className="mx-auto max-w-7xl space-y-4">{header}<Skeleton className="h-80 w-full" /></div>;
  }
  if (!snap || !report) {
    return <div className="mx-auto max-w-7xl space-y-4">{header}<EmptyState /></div>;
  }

  const m = snap.metrics;
  const priceSeries = mockPriceSeriesFor(snap.ticker);
  const lastPx = priceSeries[priceSeries.length - 1].price;
  const firstPx = priceSeries[0].price;
  const pxChange = ((lastPx - firstPx) / firstPx) * 100;
  const cur = m.currency === "INR" ? "₹" : "$";

  const incomeBars = [
    { name: "Revenue", value: (m.revenue ?? 0) / 1e9 },
    { name: "Net inc.", value: (m.net_income ?? 0) / 1e9 },
    { name: "Op. CF", value: (m.operating_cash_flow ?? 0) / 1e9 },
    { name: "FCF", value: (m.free_cash_flow ?? 0) / 1e9 },
  ];
  const riskAxes = [
    { axis: "Market", value: report.risk.risk_score },
    { axis: "Financial", value: Math.max(1, 11 - report.financials.financial_health_score) },
    { axis: "Business", value: report.risk.risk_score },
    { axis: "Valuation", value: Math.min(10, (m.pe_ratio ?? 20) / 5) },
    { axis: "Liquidity", value: Math.max(1, 11 - report.financials.financial_health_score) },
  ];

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      {header}

      <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label="Price (indicative)" value={`${cur}${lastPx.toFixed(2)}`} tone={pxChange >= 0 ? "up" : "down"} sub={`${pxChange >= 0 ? "+" : ""}${pxChange.toFixed(1)}% (60d)`} />
        <StatCard label="Market cap" value={fmtCurrency(m.market_cap)} />
        <StatCard label="P/E" value={fmtNumber(m.pe_ratio)} tone="warn" />
        <StatCard label="EPS" value={fmtNumber(m.eps)} />
        <StatCard label="Revenue" value={fmtCurrency(m.revenue)} tone="up" />
        <StatCard label="FCF" value={fmtCurrency(m.free_cash_flow)} tone="up" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>Price trend (60d)</CardTitle>
            <Badge variant="info">indicative</Badge>
          </CardHeader>
          <CardContent><PriceArea data={priceSeries} /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Risk decomposition</CardTitle></CardHeader>
          <CardContent><RiskRadar data={riskAxes} /></CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Income & cash flow ({cur}B, latest FY)</CardTitle></CardHeader>
          <CardContent><MetricBars data={incomeBars} /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Provenance</CardTitle></CardHeader>
          <CardContent>
            <p className="mb-2 text-xs text-muted-foreground">Which source supplied each field:</p>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(snap.field_sources).map(([k, v]) => (
                <Badge key={k} variant="secondary" className="mono">{k} → {v}</Badge>
              ))}
            </div>
            <p className="mt-3 text-sm text-foreground/85">{report.financials.growth_trend}</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

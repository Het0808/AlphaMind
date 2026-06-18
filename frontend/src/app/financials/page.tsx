"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SectionHeading } from "@/components/shared/SectionHeading";
import { TickerInput } from "@/components/shared/TickerInput";
import { StatCard } from "@/components/shared/StatCard";
import { PriceArea, MetricBars, RiskRadar } from "@/components/charts/Charts";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { DEFAULT_TICKER } from "@/lib/constants";
import { mockPriceSeriesFor } from "@/lib/mock";
import { fmtCurrency, fmtNumber } from "@/lib/utils";
import type { FinancialSnapshot, InvestmentReport } from "@/lib/types";

export default function FinancialDashboard() {
  const [snap, setSnap] = React.useState<FinancialSnapshot | null>(null);
  const [report, setReport] = React.useState<InvestmentReport | null>(null);
  const [loading, setLoading] = React.useState(true);

  const run = React.useCallback(async (ticker: string) => {
    setLoading(true);
    const [s, r] = await Promise.all([api.snapshot(ticker), api.analyze(ticker)]);
    setSnap(s.data); setReport(r.data);
    setLoading(false);
  }, []);

  React.useEffect(() => { run(DEFAULT_TICKER); }, [run]);

  if (loading || !snap || !report) {
    return (
      <div className="mx-auto max-w-7xl space-y-4">
        <SectionHeading title="Financial Dashboard" subtitle="Charts, fundamentals and risk decomposition" />
        <Skeleton className="h-80 w-full" />
      </div>
    );
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
    { axis: "Market", value: 8 },
    { axis: "Financial", value: 2 },
    { axis: "Business", value: 6 },
    { axis: "Valuation", value: 7 },
    { axis: "Liquidity", value: 2 },
  ];

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <SectionHeading
        title="Financial Dashboard"
        subtitle={`${snap.overview.name} · ${m.fiscal_period}`}
        right={<TickerInput loading={loading} onSubmit={run} />}
      />

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
          <CardHeader><CardTitle>Income & cash flow ($B, latest FY)</CardTitle></CardHeader>
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

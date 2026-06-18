"use client";

import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SectionHeading } from "@/components/shared/SectionHeading";
import { TickerInput } from "@/components/shared/TickerInput";
import { StatCard } from "@/components/shared/StatCard";
import { MetricBars, RiskRadar } from "@/components/charts/Charts";
import { EmptyState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { useCompanyStore } from "@/lib/store";
import { useCurrencyStore } from "@/lib/currency";
import { formatMoney, nativeSymbol, toINR } from "@/lib/currency-format";
import { fmtNumber, fmtPct } from "@/lib/utils";

const UNAVAILABLE = <span className="text-muted-foreground">Data unavailable</span>;

export default function FinancialDashboard() {
  const snap = useCompanyStore((s) => s.financialData);
  const report = useCompanyStore((s) => s.analysisData);
  const loading = useCompanyStore((s) => s.loading);
  const selectedTicker = useCompanyStore((s) => s.selectedTicker);
  const rate = useCurrencyStore((s) => s.rate);

  const header = (
    <SectionHeading
      title="Financial Dashboard"
      subtitle={snap ? `${snap.overview.name} · ${snap.metrics.fiscal_period ?? "live data"}` : "Live fundamentals, validated"}
      right={<TickerInput />}
    />
  );

  if (loading || (selectedTicker && !snap)) {
    return <div className="mx-auto max-w-7xl space-y-4">{header}<Skeleton className="h-80 w-full" /></div>;
  }
  if (!snap) {
    return <div className="mx-auto max-w-7xl space-y-4">{header}<EmptyState /></div>;
  }

  const m = snap.metrics;
  const cur = m.currency === "INR" ? "₹" : "$";
  // Fail-safe: null/unverified → "Data unavailable", never a guess.
  const money = (v?: number | null) => (v == null ? UNAVAILABLE : formatMoney(v, m.currency, rate));
  const num = (v?: number | null) => (v == null ? UNAVAILABLE : fmtNumber(v));
  const conf = snap.quality?.overall_confidence ?? 0;

  const toBar = (v?: number | null) => (v == null ? 0 : toINR(v, m.currency, rate) / 1e12);
  const incomeBars = [
    { name: "Revenue", value: toBar(m.revenue) },
    { name: "Net inc.", value: toBar(m.net_income) },
    { name: "Op. CF", value: toBar(m.operating_cash_flow) },
    { name: "FCF", value: toBar(m.free_cash_flow) },
  ];
  const riskAxes = report ? [
    { axis: "Market", value: report.risk.risk_score },
    { axis: "Financial", value: Math.max(1, 11 - report.financials.financial_health_score) },
    { axis: "Business", value: report.risk.risk_score },
    { axis: "Valuation", value: Math.min(10, (m.pe_ratio ?? 20) / 5) },
    { axis: "Liquidity", value: Math.max(1, 11 - report.financials.financial_health_score) },
  ] : [];

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      {header}

      <div className="flex items-center justify-between">
        <span className="label">Monetary values in INR{m.currency !== "INR" ? ` · converted @ ₹${rate.toFixed(2)}/USD` : ""} · live verified data only</span>
        {snap.warnings.length > 0 && <Badge variant="warn">{snap.warnings.length} data warning(s)</Badge>}
      </div>

      <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-6">
        <StatCard label={`Price (${cur})`} value={m.price == null ? UNAVAILABLE : `${cur}${fmtNumber(m.price)}`} />
        <StatCard label="Market cap (INR)" value={money(m.market_cap)} />
        <StatCard label="P/E (ratio)" value={num(m.pe_ratio)} tone="warn" />
        <StatCard label="EPS (not converted)" value={m.eps == null ? UNAVAILABLE : `${nativeSymbol(m.currency)}${fmtNumber(m.eps)}`} />
        <StatCard label="Revenue (INR)" value={money(m.revenue)} tone="up" />
        <StatCard label="FCF (INR)" value={money(m.free_cash_flow)} tone="up" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2"><ShieldCheck className="h-4 w-4" /> Data quality</CardTitle>
            <Badge variant={conf >= 0.8 ? "bull" : conf >= 0.5 ? "warn" : "bear"}>{fmtPct(conf, 0)} confidence</Badge>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-foreground/85">
            <p>Sources: <span className="mono">{snap.providers_used.join(", ") || "none"}</span></p>
            <p className="text-xs text-muted-foreground">
              Metrics below the confidence threshold are hidden as “Data unavailable” rather than shown as estimates.
            </p>
            <Link href="/quality" className="inline-flex text-xs font-medium text-primary hover:underline">
              View full data-quality report →
            </Link>
          </CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Risk decomposition</CardTitle></CardHeader>
          <CardContent>{report ? <RiskRadar data={riskAxes} /> : <p className="text-xs text-muted-foreground">Awaiting analysis.</p>}</CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Income & cash flow (₹ Lakh Cr, latest FY)</CardTitle></CardHeader>
          <CardContent><MetricBars data={incomeBars} /></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Provenance</CardTitle></CardHeader>
          <CardContent>
            <p className="mb-2 text-xs text-muted-foreground">Which source supplied each field:</p>
            <div className="flex flex-wrap gap-1.5">
              {Object.keys(snap.field_sources).length === 0
                ? <span className="text-xs text-muted-foreground">No verified sources available.</span>
                : Object.entries(snap.field_sources).map(([k, v]) => (
                    <Badge key={k} variant="secondary" className="mono">{k} → {v}</Badge>
                  ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

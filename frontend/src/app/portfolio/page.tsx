"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Progress } from "@/components/ui/progress";
import { SectionHeading } from "@/components/shared/SectionHeading";
import { StatCard } from "@/components/shared/StatCard";
import { RecommendationBadge } from "@/components/shared/RecommendationBadge";
import { MetricBars } from "@/components/charts/Charts";
import { mockPortfolio } from "@/lib/mock";
import { fmtPct } from "@/lib/utils";

export default function PortfolioAdvisor() {
  const holdings = mockPortfolio;
  const wAvgConviction = holdings.reduce((a, h) => a + h.conviction * h.weight, 0);
  const wAvgRisk = holdings.reduce((a, h) => a + h.riskScore * h.weight, 0);
  const buys = holdings.filter((h) => h.recommendation.includes("BUY")).length;

  const sectorAlloc = Object.entries(
    holdings.reduce<Record<string, number>>((acc, h) => {
      acc[h.sector] = (acc[h.sector] ?? 0) + h.weight;
      return acc;
    }, {}),
  ).map(([name, value]) => ({ name, value: Number((value * 100).toFixed(1)) }));

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <SectionHeading title="Portfolio Advisor" subtitle="Aggregated agent views across your holdings" />

      <div className="grid gap-4 sm:grid-cols-4">
        <StatCard label="Holdings" value={holdings.length} />
        <StatCard label="Wtd. conviction" value={`${wAvgConviction.toFixed(1)}/10`} tone="up" />
        <StatCard label="Wtd. risk" value={`${wAvgRisk.toFixed(1)}/10`} tone="warn" />
        <StatCard label="Buy-rated" value={`${buys}/${holdings.length}`} tone="up" />
      </div>

      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr]">
        <Card>
          <CardHeader><CardTitle>Holdings & agent recommendations</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Ticker</TableHead>
                  <TableHead>Sector</TableHead>
                  <TableHead>Weight</TableHead>
                  <TableHead>Call</TableHead>
                  <TableHead>Conviction</TableHead>
                  <TableHead>Risk</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {holdings.map((h) => (
                  <TableRow key={h.ticker}>
                    <TableCell className="mono font-semibold">{h.ticker}<div className="text-[10px] font-normal text-muted-foreground">{h.name}</div></TableCell>
                    <TableCell className="text-xs text-muted-foreground">{h.sector}</TableCell>
                    <TableCell className="mono">{fmtPct(h.weight, 0)}</TableCell>
                    <TableCell><RecommendationBadge value={h.recommendation} /></TableCell>
                    <TableCell className="w-28">
                      <div className="flex items-center gap-2">
                        <Progress value={h.conviction * 10} className="h-1.5" />
                        <span className="mono text-xs">{h.conviction}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className={`mono text-xs ${h.riskScore >= 7 ? "text-bear" : h.riskScore >= 5 ? "text-warn" : "text-bull"}`}>
                        {h.riskScore}/10
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Sector allocation (%)</CardTitle></CardHeader>
          <CardContent><MetricBars data={sectorAlloc} /></CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Advisor notes</CardTitle></CardHeader>
        <CardContent className="text-sm text-foreground/85">
          Portfolio tilts heavily to Technology (high weighted conviction but elevated weighted risk).
          Consider trimming the lowest-conviction, highest-risk position (XOM, Sell-rated, risk 7/10) and
          rebalancing toward Buy-rated, lower-risk names (MSFT). Concentration risk is the main flag.
        </CardContent>
      </Card>
    </div>
  );
}

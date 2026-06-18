"use client";

import * as React from "react";
import { ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SectionHeading } from "@/components/shared/SectionHeading";
import { TickerInput } from "@/components/shared/TickerInput";
import { StatCard } from "@/components/shared/StatCard";
import { EmptyState } from "@/components/shared/EmptyState";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { useCompanyStore } from "@/lib/store";
import { fmtPct } from "@/lib/utils";
import type { QualityReport } from "@/lib/types";

const STATUS_VARIANT: Record<string, "bull" | "warn" | "bear" | "info" | "secondary"> = {
  ok: "bull", single_source: "info", disagreement: "warn", out_of_range: "bear", unavailable: "secondary",
};

export default function DataQualityDashboard() {
  const selectedTicker = useCompanyStore((s) => s.selectedTicker);
  const company = useCompanyStore((s) => s.selectedCompany);
  const [report, setReport] = React.useState<QualityReport | null>(null);
  const [retrievedAt, setRetrievedAt] = React.useState<string>("");
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (!selectedTicker) return;
    setLoading(true);
    api.quality(selectedTicker).then(({ data }) => {
      setReport(data.quality);
      setRetrievedAt(data.retrieved_at);
      setLoading(false);
    });
  }, [selectedTicker]);

  const overall = report?.overall_confidence ?? 0;
  const ShieldIcon = overall >= 0.8 ? ShieldCheck : overall >= 0.5 ? ShieldAlert : ShieldX;

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <SectionHeading
        title="Data Quality Dashboard"
        subtitle={selectedTicker ? `Source provenance, validation & confidence · ${company} (${selectedTicker})` : "Source provenance, validation & confidence"}
        right={<TickerInput />}
      />

      {loading ? (
        <Skeleton className="h-80 w-full" />
      ) : !report ? (
        <EmptyState title="No quality report" hint="Live financial data unavailable for this ticker." />
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-4">
            <StatCard label="Overall confidence" value={
              <span className="flex items-center gap-2"><ShieldIcon className="h-5 w-5" /> {fmtPct(overall, 0)}</span>
            } tone={overall >= 0.8 ? "up" : overall >= 0.5 ? "warn" : "down"} />
            <StatCard label="Providers" value={report.providers.join(", ") || "—"} />
            <StatCard label="Last update" value={retrievedAt ? new Date(retrievedAt).toLocaleString() : "—"} />
            <StatCard label="Validation flags" value={report.validations.length} tone={report.validations.length ? "warn" : "up"} />
          </div>

          <Card>
            <CardHeader><CardTitle>Per-metric data quality</CardTitle></CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Metric</TableHead><TableHead>Value</TableHead><TableHead>Source</TableHead>
                    <TableHead>Agreement</TableHead><TableHead>Confidence</TableHead><TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.values(report.field_quality)
                    .sort((a, b) => b.confidence - a.confidence)
                    .map((q) => (
                    <TableRow key={q.field}>
                      <TableCell className="text-xs font-medium">{q.field}</TableCell>
                      <TableCell className="mono text-xs">
                        {q.value == null ? <span className="text-muted-foreground">Data unavailable</span> : q.value.toLocaleString()}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {Object.keys(q.sources).join(", ") || "—"}
                      </TableCell>
                      <TableCell className="mono text-xs">{q.agreement == null ? "—" : fmtPct(q.agreement, 0)}</TableCell>
                      <TableCell className="w-24">
                        <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                          <div className={`h-full rounded-full ${q.confidence >= 0.8 ? "bg-bull" : q.confidence >= 0.5 ? "bg-warn" : "bg-bear"}`} style={{ width: `${q.confidence * 100}%` }} />
                        </div>
                        <span className="mono text-[10px] text-muted-foreground">{fmtPct(q.confidence, 0)}</span>
                      </TableCell>
                      <TableCell><Badge variant={STATUS_VARIANT[q.status] ?? "secondary"}>{q.status}</Badge></TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {report.validations.length > 0 && (
            <Card>
              <CardHeader><CardTitle>Validation messages</CardTitle></CardHeader>
              <CardContent className="space-y-1">
                {report.validations.map((v, i) => (
                  <p key={i} className="mono text-xs text-foreground/80">{v}</p>
                ))}
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

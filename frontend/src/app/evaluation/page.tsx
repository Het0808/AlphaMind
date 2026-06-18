"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SectionHeading } from "@/components/shared/SectionHeading";
import { StatCard } from "@/components/shared/StatCard";
import { ScoreBars } from "@/components/charts/Charts";
import { Skeleton } from "@/components/ui/skeleton";
import { api } from "@/lib/api";
import { fmtPct } from "@/lib/utils";
import type { EvalReport } from "@/lib/types";

export default function EvaluationDashboard() {
  const [report, setReport] = React.useState<EvalReport | null>(null);

  React.useEffect(() => { api.evalReport().then(({ data }) => setReport(data)); }, []);

  if (!report) {
    return (
      <div className="mx-auto max-w-7xl space-y-4">
        <SectionHeading title="Evaluation Dashboard" subtitle="Faithfulness, hallucination, retrieval, tools, completeness" />
        <Skeleton className="h-80 w-full" />
      </div>
    );
  }

  const metricRows = Object.entries(report.metric_averages).map(([name, value]) => ({
    name, value, pass: report.pass_rates[name],
  }));
  const scoreBarData = metricRows.map((r) => ({ name: r.name, value: r.value }));

  return (
    <div className="mx-auto max-w-7xl space-y-5">
      <SectionHeading
        title="Evaluation Dashboard"
        subtitle={`Run ${report.run_id} · ${report.n_samples} samples`}
        right={<Badge variant={report.overall_quality >= 0.8 ? "bull" : "warn"}>Quality {fmtPct(report.overall_quality, 0)}</Badge>}
      />

      <div className="grid gap-4 sm:grid-cols-4">
        <StatCard label="Overall quality" value={fmtPct(report.overall_quality, 0)} tone="up" />
        <StatCard label="Samples" value={report.n_samples} />
        <StatCard label="Metrics" value={metricRows.length} />
        <StatCard label="Failures" value={report.failures.length} tone="warn" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Evaluation scores</CardTitle></CardHeader>
          <CardContent><ScoreBars data={scoreBarData} /></CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Metrics · average & pass rate</CardTitle></CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow><TableHead>Metric</TableHead><TableHead>Average</TableHead><TableHead>Pass rate</TableHead></TableRow>
              </TableHeader>
              <TableBody>
                {metricRows.map((r) => (
                  <TableRow key={r.name}>
                    <TableCell className="text-xs">{r.name}</TableCell>
                    <TableCell className="mono">{fmtPct(r.value, 0)}</TableCell>
                    <TableCell>
                      <span className={`mono text-xs ${r.pass >= 0.8 ? "text-bull" : r.pass >= 0.6 ? "text-warn" : "text-bear"}`}>
                        {fmtPct(r.pass, 0)}
                      </span>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Agent performance</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Agent</TableHead>
                <TableHead>Faithfulness</TableHead>
                <TableHead>Retrieval</TableHead>
                <TableHead>Tool use</TableHead>
                <TableHead>Completeness</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(report.agent_breakdown).map(([agent, metrics]) => (
                <TableRow key={agent}>
                  <TableCell className="font-medium capitalize">{agent}</TableCell>
                  <TableCell className="mono">{cell(metrics.faithfulness)}</TableCell>
                  <TableCell className="mono">{cell(metrics.retrieval_quality)}</TableCell>
                  <TableCell className="mono">{cell(metrics.tool_usage_accuracy)}</TableCell>
                  <TableCell className="mono">{cell(metrics.response_completeness)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Failure analysis</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Sample</TableHead><TableHead>Agent</TableHead><TableHead>Metric</TableHead>
                <TableHead>Score</TableHead><TableHead>Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {report.failures.map((f, i) => (
                <TableRow key={i}>
                  <TableCell className="mono text-xs">{f.sample_id}</TableCell>
                  <TableCell className="text-xs capitalize">{f.agent ?? "—"}</TableCell>
                  <TableCell><Badge variant="bear">{f.metric}</Badge></TableCell>
                  <TableCell className="mono text-bear">{f.score.toFixed(2)}</TableCell>
                  <TableCell className="text-xs text-muted-foreground">{f.reason}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

function cell(v?: number) {
  return v == null ? "—" : `${Math.round(v * 100)}%`;
}

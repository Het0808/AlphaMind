"""Aggregate per-sample scores into an EvalReport with failure analysis.

Skipped metrics (no data to score) are excluded from averages and pass rates so
they neither inflate nor deflate results. `overall_quality` normalizes each metric
by its direction (hallucination is inverted) before averaging.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from statistics import mean
from typing import Dict, List

from .schemas import EvalReport, FailureCase, SampleResult


def build_report(results: List[SampleResult], *, run_id: str | None = None) -> EvalReport:
    run_id = run_id or f"eval-{uuid.uuid4().hex[:8]}"

    scores_by_metric: Dict[str, List[float]] = defaultdict(list)
    passes_by_metric: Dict[str, List[bool]] = defaultdict(list)
    direction: Dict[str, bool] = {}
    agent_scores: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))
    failures: List[FailureCase] = []

    for res in results:
        for s in res.scores:
            direction[s.metric] = s.higher_is_better
            if s.skipped:
                continue
            scores_by_metric[s.metric].append(s.score)
            passes_by_metric[s.metric].append(s.passed)
            if res.agent:
                agent_scores[res.agent][s.metric].append(s.score)
            if not s.passed:
                failures.append(FailureCase(
                    sample_id=res.sample_id, agent=res.agent, metric=s.metric,
                    score=s.score, question=res.question, reason=s.detail or "below threshold",
                ))

    metric_averages = {m: round(mean(v), 4) for m, v in scores_by_metric.items() if v}
    pass_rates = {m: round(sum(v) / len(v), 4) for m, v in passes_by_metric.items() if v}
    agent_breakdown = {
        agent: {m: round(mean(v), 4) for m, v in metrics.items() if v}
        for agent, metrics in agent_scores.items()
    }

    # Direction-normalized overall quality.
    normalized = [
        (avg if direction.get(m, True) else 1 - avg)
        for m, avg in metric_averages.items()
    ]
    overall_quality = round(mean(normalized), 4) if normalized else 0.0

    return EvalReport(
        run_id=run_id,
        n_samples=len(results),
        overall_quality=overall_quality,
        metric_averages=metric_averages,
        pass_rates=pass_rates,
        agent_breakdown=agent_breakdown,
        failures=failures,
        results=results,
    )

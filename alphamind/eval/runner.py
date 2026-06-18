"""EvaluationRunner — score a dataset across all metrics and build a report.

`target` is a callable mapping an EvalSample to the system's AgentOutput (e.g. an
adapter over the analyze pipeline or the RAG retriever). For offline scoring of
pre-computed outputs, pass a target that just returns them.
"""

from __future__ import annotations

import logging
from typing import Callable, List, Optional

from .metrics import BaseMetric, default_metrics
from .report import build_report
from .schemas import AgentOutput, EvalReport, EvalSample, SampleResult

logger = logging.getLogger(__name__)

Target = Callable[[EvalSample], AgentOutput]


class EvaluationRunner:
    def __init__(self, metrics: Optional[List[BaseMetric]] = None, settings=None):
        self.metrics = metrics or default_metrics(settings)

    def evaluate_sample(self, sample: EvalSample, output: AgentOutput) -> SampleResult:
        scores = [m.evaluate(sample, output) for m in self.metrics]
        failed = [s.metric for s in scores if not s.passed and not s.skipped]
        return SampleResult(
            sample_id=sample.id, agent=sample.agent, question=sample.question,
            output=output, scores=scores, failed_metrics=failed,
        )

    def run(
        self,
        samples: List[EvalSample],
        target: Target,
        *,
        run_id: Optional[str] = None,
        push_to_langsmith: bool = False,
    ) -> EvalReport:
        results: List[SampleResult] = []
        for sample in samples:
            try:
                output = target(sample)
            except Exception as exc:  # noqa: BLE001 - a failing run is itself a result
                logger.warning("Target failed on %s: %s", sample.id, exc)
                output = AgentOutput(answer="", metadata={"error": str(exc)})
            results.append(self.evaluate_sample(sample, output))

        report = build_report(results, run_id=run_id)

        if push_to_langsmith:
            try:
                from .langsmith_eval import push_report

                push_report(report)
            except Exception as exc:  # noqa: BLE001
                logger.warning("LangSmith push failed: %s", exc)

        return report

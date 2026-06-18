"""LangSmith integration — datasets, evaluation runs, and feedback.

Lets you (a) push an EvalReport's per-metric scores as feedback / a run summary to
LangSmith, and (b) turn AlphaMind metrics into LangSmith evaluators for use with
`langsmith.evaluate`. All imports are lazy and failures are non-fatal.
"""

from __future__ import annotations

import logging
from typing import Callable, List

from ..config import get_settings
from .metrics import BaseMetric, default_metrics
from .schemas import AgentOutput, EvalSample, EvalReport

logger = logging.getLogger(__name__)


def get_client():
    """Return a LangSmith client, or None if unavailable/unconfigured."""
    settings = get_settings()
    if not (settings.langsmith_api_key or settings.langchain_tracing_v2):
        return None
    try:
        from langsmith import Client

        return Client(api_key=settings.langsmith_api_key or None)
    except Exception as exc:  # noqa: BLE001
        logger.warning("LangSmith client unavailable: %s", exc)
        return None


def push_report(report: EvalReport) -> bool:
    """Record an evaluation run's aggregate scores in LangSmith as a project run."""
    client = get_client()
    if client is None:
        return False
    settings = get_settings()
    try:
        client.create_run(
            name=f"alphamind-eval:{report.run_id}",
            run_type="chain",
            project_name=settings.langsmith_project,
            inputs={"n_samples": report.n_samples},
            outputs={
                "overall_quality": report.overall_quality,
                "metric_averages": report.metric_averages,
                "pass_rates": report.pass_rates,
                "n_failures": len(report.failures),
            },
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("LangSmith push_report failed: %s", exc)
        return False


def to_langsmith_evaluators(metrics: List[BaseMetric] | None = None) -> List[Callable]:
    """Adapt AlphaMind metrics into LangSmith evaluator callables.

    Each evaluator maps a LangSmith (run, example) pair onto a {key, score} dict.
    """
    metrics = metrics or default_metrics(get_settings())

    def make(metric: BaseMetric) -> Callable:
        def _evaluator(run, example) -> dict:
            sample = EvalSample(
                id=str(getattr(example, "id", "ex")),
                question=(example.inputs or {}).get("question", ""),
                contexts=(example.inputs or {}).get("contexts", []),
                reference=(example.outputs or {}).get("reference"),
                reference_contexts=(example.outputs or {}).get("reference_contexts", []),
                expected_tools=(example.outputs or {}).get("expected_tools", []),
                required_points=(example.outputs or {}).get("required_points", []),
            )
            out = run.outputs or {}
            output = AgentOutput(
                answer=out.get("answer", ""),
                contexts=out.get("contexts", []),
                tool_calls=out.get("tool_calls", []),
            )
            result = metric.evaluate(sample, output)
            return {"key": metric.name, "score": result.score, "comment": result.detail}

        return _evaluator

    return [make(m) for m in metrics]

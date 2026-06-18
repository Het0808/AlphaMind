"""AlphaMind LLM evaluation framework.

Scores agent outputs across five metrics — Faithfulness, Hallucination rate,
Retrieval quality, Tool-usage accuracy, and Response completeness — aggregates
them into a report with failure analysis, and integrates with LangSmith (tracing /
datasets / feedback) and Ragas (reference metrics).

The deterministic metric cores and the report builder have no heavy dependencies,
so they're fully unit-testable; LangSmith/Ragas are imported lazily.
"""

from .metrics import default_metrics
from .report import build_report
from .runner import EvaluationRunner
from .schemas import (
    AgentOutput,
    EvalReport,
    EvalSample,
    FailureCase,
    MetricScore,
    SampleResult,
)

__all__ = [
    "EvalSample",
    "AgentOutput",
    "MetricScore",
    "SampleResult",
    "FailureCase",
    "EvalReport",
    "default_metrics",
    "build_report",
    "EvaluationRunner",
]

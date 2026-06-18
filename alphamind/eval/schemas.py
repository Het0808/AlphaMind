"""Data contracts for evaluation: samples, outputs, scores, and the report."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvalSample(BaseModel):
    """One evaluation case (optionally with references / expectations)."""

    id: str
    question: str
    agent: Optional[str] = None  # which agent/component produced/should produce the answer
    contexts: List[str] = Field(default_factory=list, description="Context the answer should be grounded in.")
    reference: Optional[str] = Field(None, description="Gold answer, if available.")
    reference_contexts: List[str] = Field(default_factory=list, description="Relevant/gold contexts for retrieval scoring.")
    expected_tools: List[str] = Field(default_factory=list, description="Tools a correct run should use.")
    required_points: List[str] = Field(default_factory=list, description="Elements a complete answer must cover.")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentOutput(BaseModel):
    """What the system actually produced for a sample."""

    answer: str = ""
    contexts: List[str] = Field(default_factory=list, description="Contexts actually retrieved/used.")
    tool_calls: List[str] = Field(default_factory=list, description="Tools actually invoked.")
    citations: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MetricScore(BaseModel):
    metric: str
    score: float = Field(..., description="Metric value in [0,1].")
    passed: bool
    higher_is_better: bool = True
    skipped: bool = Field(False, description="True when the sample lacked data to score this metric.")
    detail: str = ""
    breakdown: Dict[str, Any] = Field(default_factory=dict)


class SampleResult(BaseModel):
    sample_id: str
    agent: Optional[str] = None
    question: str
    output: AgentOutput
    scores: List[MetricScore]
    failed_metrics: List[str] = Field(default_factory=list)


class FailureCase(BaseModel):
    sample_id: str
    agent: Optional[str] = None
    metric: str
    score: float
    question: str
    reason: str


class EvalReport(BaseModel):
    run_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    n_samples: int
    overall_quality: float = Field(0.0, description="Mean of direction-normalized metric averages.")
    metric_averages: Dict[str, float] = Field(default_factory=dict)
    pass_rates: Dict[str, float] = Field(default_factory=dict)
    agent_breakdown: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    failures: List[FailureCase] = Field(default_factory=list)
    results: List[SampleResult] = Field(default_factory=list)

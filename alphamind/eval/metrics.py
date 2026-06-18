"""The five evaluation metrics.

Each metric has a deterministic, dependency-free core so it can run (and be tested)
without an LLM. Ragas can replace the faithfulness / retrieval metrics with
LLM-graded versions when references are available (see `ragas_eval.py`).

  • Faithfulness        — fraction of answer claims supported by the context.
  • Hallucination rate  — fraction of claims NOT supported (lower is better).
  • Retrieval quality   — F1 of retrieved vs. gold-relevant contexts.
  • Tool-usage accuracy — F1 of tools used vs. expected.
  • Response completeness — fraction of required points covered by the answer.
"""

from __future__ import annotations

import re
from typing import List, Sequence, Set, Tuple

from .schemas import AgentOutput, EvalSample, MetricScore

_STOPWORDS = {
    "the", "a", "an", "of", "to", "and", "in", "is", "are", "for", "on", "with",
    "that", "this", "it", "as", "by", "at", "be", "or", "was", "were", "from",
    "has", "have", "had", "will", "its", "their", "than", "into", "we", "our",
}


def tokenize(text: str) -> Set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in _STOPWORDS}


def coverage(target: Set[str], source: Set[str]) -> float:
    """Fraction of `target` tokens present in `source`."""
    if not target:
        return 1.0
    return len(target & source) / len(target)


def split_claims(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if re.search(r"[a-z0-9]", p, re.I)]


def claim_support(answer: str, contexts: Sequence[str], *, thresh: float = 0.5) -> Tuple[int, int, List[str]]:
    """Return (supported, total, unsupported_claims) for an answer vs its contexts."""
    claims = split_claims(answer)
    if not claims:
        return 0, 0, []
    ctx_tokens: Set[str] = set()
    for c in contexts:
        ctx_tokens |= tokenize(c)
    supported, unsupported = 0, []
    for claim in claims:
        if coverage(tokenize(claim), ctx_tokens) >= thresh:
            supported += 1
        else:
            unsupported.append(claim)
    return supported, len(claims), unsupported


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0


# ── Metric base ─────────────────────────────────────────────────────────────
class BaseMetric:
    name: str = "metric"
    higher_is_better: bool = True

    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold

    def _passed(self, score: float) -> bool:
        return score >= self.threshold if self.higher_is_better else score <= self.threshold

    def _score(self, score: float, *, detail: str = "", breakdown: dict | None = None, skipped: bool = False) -> MetricScore:
        return MetricScore(
            metric=self.name, score=round(score, 4),
            passed=True if skipped else self._passed(score),
            higher_is_better=self.higher_is_better, skipped=skipped,
            detail=detail, breakdown=breakdown or {},
        )

    def evaluate(self, sample: EvalSample, output: AgentOutput) -> MetricScore:  # pragma: no cover - interface
        raise NotImplementedError


# ── Concrete metrics ────────────────────────────────────────────────────────
class Faithfulness(BaseMetric):
    name = "faithfulness"

    def evaluate(self, sample, output):
        contexts = output.contexts or sample.contexts
        if not contexts:
            return self._score(0.0, detail="no context to check faithfulness against", skipped=True)
        supported, total, unsupported = claim_support(output.answer, contexts)
        if total == 0:
            return self._score(1.0, detail="no factual claims in answer")
        score = supported / total
        return self._score(score, detail=f"{supported}/{total} claims supported",
                           breakdown={"unsupported": unsupported[:5]})


class HallucinationRate(BaseMetric):
    name = "hallucination_rate"
    higher_is_better = False

    def __init__(self, threshold: float = 0.2):
        super().__init__(threshold)

    def evaluate(self, sample, output):
        contexts = output.contexts or sample.contexts
        if not contexts:
            return self._score(0.0, detail="no context to check hallucination against", skipped=True)
        supported, total, unsupported = claim_support(output.answer, contexts)
        if total == 0:
            return self._score(0.0, detail="no factual claims in answer")
        rate = len(unsupported) / total
        return self._score(rate, detail=f"{len(unsupported)}/{total} claims unsupported",
                           breakdown={"unsupported": unsupported[:5]})


class RetrievalQuality(BaseMetric):
    name = "retrieval_quality"

    def evaluate(self, sample, output):
        relevant = sample.reference_contexts
        retrieved = output.contexts
        if not relevant:
            return self._score(0.0, detail="no gold contexts provided", skipped=True)
        rel_tokens = [tokenize(r) for r in relevant]
        ret_tokens = [tokenize(r) for r in retrieved]
        matched_retrieved = sum(1 for rt in ret_tokens if any(coverage(g, rt) >= 0.5 for g in rel_tokens))
        matched_relevant = sum(1 for g in rel_tokens if any(coverage(g, rt) >= 0.5 for rt in ret_tokens))
        precision = matched_retrieved / len(retrieved) if retrieved else 0.0
        recall = matched_relevant / len(relevant)
        score = _f1(precision, recall)
        return self._score(score, detail=f"precision={precision:.2f}, recall={recall:.2f}",
                           breakdown={"precision": round(precision, 3), "recall": round(recall, 3)})


class ToolUsageAccuracy(BaseMetric):
    name = "tool_usage_accuracy"

    def evaluate(self, sample, output):
        expected = set(sample.expected_tools)
        if not expected:
            return self._score(0.0, detail="no expected tools specified", skipped=True)
        actual = set(output.tool_calls)
        tp = len(expected & actual)
        precision = tp / len(actual) if actual else 0.0
        recall = tp / len(expected)
        score = _f1(precision, recall)
        return self._score(
            score,
            detail=f"missing={sorted(expected - actual)}, unexpected={sorted(actual - expected)}",
            breakdown={"precision": round(precision, 3), "recall": round(recall, 3),
                       "missing": sorted(expected - actual), "unexpected": sorted(actual - expected)},
        )


class ResponseCompleteness(BaseMetric):
    name = "response_completeness"

    def evaluate(self, sample, output):
        points = sample.required_points
        if not points:
            return self._score(1.0, detail="no completeness criteria", skipped=True)
        answer_tokens = tokenize(output.answer)
        answer_lower = output.answer.lower()
        covered = [p for p in points
                   if p.lower() in answer_lower or coverage(tokenize(p), answer_tokens) >= 0.6]
        score = len(covered) / len(points)
        missing = [p for p in points if p not in covered]
        return self._score(score, detail=f"{len(covered)}/{len(points)} required points covered",
                           breakdown={"missing": missing})


def default_metrics(settings=None) -> List[BaseMetric]:
    """The standard AlphaMind metric suite."""
    t = (settings.eval_threshold if settings else 0.7)
    return [
        Faithfulness(t),
        HallucinationRate(0.2),
        RetrievalQuality(t),
        ToolUsageAccuracy(t),
        ResponseCompleteness(t),
    ]

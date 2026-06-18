"""Ragas integration — LLM-graded faithfulness and retrieval metrics.

Maps AlphaMind samples/outputs onto Ragas `SingleTurnSample`s and runs Ragas
metrics (faithfulness, answer relevancy, context precision/recall). Imported
lazily and degrades to an empty result if Ragas isn't installed/configured.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from .schemas import AgentOutput, EvalSample

logger = logging.getLogger(__name__)


def run_ragas(samples: List[EvalSample], outputs: List[AgentOutput]) -> Dict[str, float]:
    """Return averaged Ragas scores, or {} if Ragas is unavailable."""
    try:
        from ragas import evaluate
        from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
        from ragas.metrics import (
            answer_relevancy,
            context_precision,
            context_recall,
            faithfulness,
        )
    except ImportError:
        logger.warning("ragas not installed; skipping Ragas metrics")
        return {}

    rows = []
    for sample, output in zip(samples, outputs):
        rows.append(SingleTurnSample(
            user_input=sample.question,
            response=output.answer,
            retrieved_contexts=output.contexts or sample.contexts,
            reference=sample.reference or "",
        ))

    try:
        result = evaluate(
            EvaluationDataset(samples=rows),
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )
        scores = result.to_pandas().mean(numeric_only=True).to_dict()
        return {k: float(v) for k, v in scores.items()}
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ragas evaluation failed: %s", exc)
        return {}

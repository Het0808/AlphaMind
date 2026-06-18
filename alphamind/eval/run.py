"""CLI: run an evaluation and write a report JSON for the dashboard.

    # Score pre-computed outputs (offline; no LLM needed):
    python -m alphamind.eval.run --outputs outputs.json

    # Run the live analyze pipeline as the target (needs OpenAI + deps):
    python -m alphamind.eval.run --live

`outputs.json` is a map of sample id -> AgentOutput fields.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Dict

from ..config import get_settings
from .datasets import default_dataset, load_dataset
from .runner import EvaluationRunner
from .schemas import AgentOutput, EvalSample


def _outputs_target(outputs: Dict[str, dict]):
    def target(sample: EvalSample) -> AgentOutput:
        return AgentOutput(**outputs.get(sample.id, {"answer": ""}))
    return target


def _live_target():
    """Adapter mapping a sample to a live AlphaMind analysis output."""
    from ..graph import analyze
    from ..schemas import AnalysisRequest

    def target(sample: EvalSample) -> AgentOutput:
        ticker = sample.metadata.get("ticker") or sample.question.split()[-1]
        report = analyze(AnalysisRequest(ticker=ticker))
        answer = report.executive_summary + " " + " ".join(report.key_thesis)
        return AgentOutput(
            answer=answer,
            contexts=list(report.research.filing_citations),
            tool_calls=[t.split(":")[0] for t in report.trace],
            citations=list(report.research.filing_citations),
        )

    return target


def main(argv=None) -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Run AlphaMind LLM evaluation.")
    parser.add_argument("--dataset", help="Path to a dataset JSON (defaults to the built-in set).")
    parser.add_argument("--outputs", help="Path to pre-computed outputs JSON (id -> output).")
    parser.add_argument("--live", action="store_true", help="Run the live analyze pipeline as the target.")
    parser.add_argument("--out", default=settings.eval_report_path, help="Where to write the report JSON.")
    parser.add_argument("--langsmith", action="store_true", help="Push the report to LangSmith.")
    args = parser.parse_args(argv)

    samples = load_dataset(args.dataset) if args.dataset else default_dataset()

    if args.live:
        target = _live_target()
    elif args.outputs:
        target = _outputs_target(json.loads(Path(args.outputs).read_text()))
    else:
        parser.error("Provide --outputs <file> or --live.")

    report = EvaluationRunner(settings=settings).run(
        samples, target, push_to_langsmith=args.langsmith
    )
    Path(args.out).write_text(report.model_dump_json(indent=2))
    print(f"overall_quality={report.overall_quality}  "
          f"averages={report.metric_averages}  failures={len(report.failures)}")
    print(f"Report written to {args.out}")


if __name__ == "__main__":
    main()

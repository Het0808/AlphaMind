"""Evaluation datasets.

A small built-in golden set exercises every metric, and `load_dataset` reads a
JSON list of samples so you can maintain larger sets outside the codebase.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from .schemas import EvalSample


def default_dataset() -> List[EvalSample]:
    return [
        EvalSample(
            id="nvda-risk-1",
            agent="research",
            question="What are NVIDIA's main risk factors?",
            contexts=[
                "NVIDIA depends on a limited number of foundry partners such as TSMC for "
                "manufacturing, creating supply concentration risk. Demand for data center "
                "GPUs is cyclical and sensitive to export controls."
            ],
            reference_contexts=[
                "NVIDIA relies on TSMC for manufacturing; export controls and supply "
                "concentration are key risks."
            ],
            expected_tools=["search_filings", "get_company_overview"],
            required_points=["supply concentration", "export controls", "data center demand"],
            metadata={"ticker": "NVDA"},
        ),
        EvalSample(
            id="aapl-fin-1",
            agent="financial",
            question="Summarize Apple's profitability and cash flow.",
            contexts=[
                "Apple reported revenue of 391 billion and net income of 94 billion with "
                "operating cash flow of 118 billion, reflecting strong margins."
            ],
            reference_contexts=[
                "Apple revenue 391B, net income 94B, operating cash flow 118B, high margins."
            ],
            expected_tools=["get_financial_snapshot"],
            required_points=["revenue", "net income", "cash flow", "margins"],
            metadata={"ticker": "AAPL"},
        ),
    ]


def load_dataset(path: str | Path) -> List[EvalSample]:
    data = json.loads(Path(path).read_text())
    return [EvalSample.model_validate(item) for item in data]

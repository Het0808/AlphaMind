"""Financial Agent — quantitative fundamentals.

Reads live valuation, profitability, growth and balance-sheet metrics and
interprets them into a financial-health verdict. Echoes the raw metrics it used
into the report for auditability.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_llm
from ..schemas import FinancialReport
from ..state import AgentState
from ..tools import get_financial_snapshot

import logging

logger = logging.getLogger(__name__)

SYSTEM = (
    "You are a buy-side financial analyst at AlphaMind. Interpret the provided "
    "fundamental metrics into a clear verdict on valuation, profitability, "
    "balance-sheet strength and growth. The data is merged from multiple sources "
    "(Yahoo Finance, SEC EDGAR, Financial Modeling Prep); the `field_sources` map "
    "tells you which source supplied each figure — trust audited SEC data most. "
    "Be quantitative where data exists and explicit when a field is missing. "
    "Populate `key_metrics` with the figures you actually relied on, and score "
    "overall financial health 1-10."
)


def financial_agent(state: AgentState) -> AgentState:
    ticker = state["ticker"].upper()
    logger.info("agent=financial ticker received: %s", ticker)
    snapshot = get_financial_snapshot(ticker)

    llm = get_llm().with_structured_output(FinancialReport)
    report: FinancialReport = llm.invoke(
        [
            SystemMessage(content=SYSTEM),
            HumanMessage(
                content=(
                    f"Ticker: {ticker}\n"
                    f"Multi-source financial snapshot:\n{snapshot}\n\n"
                    "Write the financial analysis."
                )
            ),
        ]
    )
    sources = ",".join(snapshot.get("providers_used", [])) or "none"
    return {
        "financial_report": report,
        "trace": [f"financial: fundamentals via [{sources}]"],
    }

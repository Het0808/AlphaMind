"""Research Agent — qualitative equity research.

Covers the business model, competitive moat, growth drivers, threats, and the
bull/bear narrative. Grounds its analysis in a live company profile and, when RAG
is enabled, in retrieved SEC filing excerpts that it must cite verbatim.
"""

from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from ..config import get_settings
from ..llm import get_llm
from ..schemas import ResearchReport
from ..state import AgentState
from ..tools import get_company_profile, search_filings

logger = logging.getLogger(__name__)

SYSTEM = (
    "You are a senior equity research analyst at AlphaMind. Produce rigorous, "
    "balanced qualitative research on the company: what it does, its economic "
    "moat, structural growth drivers, competitive threats, and a crisp bull and "
    "bear case. Ground every claim in the provided profile and your knowledge; "
    "do not invent precise figures. When SEC filing excerpts are provided, prefer "
    "them as evidence and populate `filing_citations` with the exact references "
    "you relied on (copy them verbatim from the excerpt headers)."
)

# Queries used to pull the most decision-relevant filing passages.
_RAG_QUERY = (
    "principal risk factors, competition, growth strategy, and management's "
    "discussion of results of operations and outlook"
)


def _filing_context(ticker: str) -> str:
    """Retrieve SEC filing excerpts (no-op string if RAG is disabled/unpopulated)."""
    if not get_settings().enable_rag:
        return ""
    hits = search_filings(ticker, _RAG_QUERY, k=6)
    results = hits.get("results") or []
    if not results:
        return ""
    excerpts = "\n".join(
        f"[{i + 1}] ({r['reference']} — {r['url']})\n{r['text'][:700]}"
        for i, r in enumerate(results)
    )
    return (
        "\n\nRELEVANT SEC FILING EXCERPTS (cite these exact references in "
        "`filing_citations`):\n" + excerpts
    )


def research_agent(state: AgentState) -> AgentState:
    ticker = state["ticker"].upper()
    logger.info("agent=research ticker received: %s", ticker)
    profile = get_company_profile(ticker)
    rag_context = _filing_context(ticker)

    llm = get_llm().with_structured_output(ResearchReport)
    report: ResearchReport = llm.invoke(
        [
            SystemMessage(content=SYSTEM),
            HumanMessage(
                content=(
                    f"Ticker: {ticker}\n"
                    f"Company profile (live data):\n{profile}\n\n"
                    f"Horizon: {state.get('horizon', '12 months')}"
                    f"{rag_context}\n\n"
                    "Write the equity research report."
                )
            ),
        ]
    )
    note = "research: completed equity research"
    if rag_context:
        note += " (RAG-grounded)"
    return {"research_report": report, "trace": [note]}

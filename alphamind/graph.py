"""LangGraph assembly — wires the supervisor and specialists into one graph.

Topology (supervisor / fan-out / fan-in):

    START
      │
      ▼
    supervisor_plan
      ├──────────────┬──────────────┐
      ▼              ▼              ▼
   research       financial        news      (parallel fan-out)
      └──────────────┴──────────────┘
                     ▼
                    risk            (fan-in: waits for all three)
                     ▼
              supervisor_synthesize
                     ▼
                    END

The three research specialists run concurrently because each writes a distinct
state key. `risk` joins on all three (LangGraph waits for every inbound edge),
then the supervisor synthesizes the final call.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from .config import get_settings
from .agents import (
    financial_agent,
    news_agent,
    research_agent,
    risk_agent,
    supervisor_plan,
    supervisor_synthesize,
)
from .schemas import AnalysisRequest, InvestmentReport
from .state import AgentState

logger = logging.getLogger(__name__)


def build_graph():
    """Construct and compile the AlphaMind agent graph."""
    g = StateGraph(AgentState)

    # Nodes
    g.add_node("supervisor_plan", supervisor_plan)
    g.add_node("research", research_agent)
    g.add_node("financial", financial_agent)
    g.add_node("news", news_agent)
    g.add_node("risk", risk_agent)
    g.add_node("supervisor_synthesize", supervisor_synthesize)

    # Entry → plan
    g.add_edge(START, "supervisor_plan")

    # Plan → fan out to the three research specialists (parallel)
    g.add_edge("supervisor_plan", "research")
    g.add_edge("supervisor_plan", "financial")
    g.add_edge("supervisor_plan", "news")

    # Fan in: risk runs only after all three specialists finish
    g.add_edge(["research", "financial", "news"], "risk")

    # Risk → synthesis → end
    g.add_edge("risk", "supervisor_synthesize")
    g.add_edge("supervisor_synthesize", END)

    return g.compile()


@lru_cache
def get_compiled_graph():
    """Cached compiled graph — compile once, reuse across requests."""
    return build_graph()


def analyze(request: AnalysisRequest) -> InvestmentReport:
    """Run the full AlphaMind pipeline and return a validated InvestmentReport.

    When `request.remember` is set and memory is enabled, prior memory is recalled
    and injected as analyst notes (so e.g. an earlier NVIDIA analysis informs a
    later AMD comparison), and the resulting report is persisted back to memory.
    """
    mem = _open_memory(request)

    notes = request.notes
    if mem is not None:
        recalled = _recall_notes(mem, request)
        if recalled:
            notes = f"{notes}\n\n{recalled}" if notes else recalled

    graph = get_compiled_graph()
    final_state: AgentState = graph.invoke(
        {
            "ticker": request.ticker.upper(),
            "horizon": request.horizon,
            "notes": notes,
            "trace": [],
        }
    )

    synthesis = final_state["synthesis"]
    report = InvestmentReport(
        ticker=request.ticker.upper(),
        company_name=final_state.get("company_name", request.ticker.upper()),
        horizon=request.horizon,
        recommendation=synthesis.recommendation,
        conviction=synthesis.conviction,
        executive_summary=synthesis.executive_summary,
        key_thesis=synthesis.key_thesis,
        key_risks=synthesis.key_risks,
        research=final_state["research_report"],
        financials=final_state["financial_report"],
        news=final_state["news_report"],
        risk=final_state["risk_report"],
        trace=final_state.get("trace", []),
    )

    if mem is not None:
        _persist(mem, request, report)
    return report


# ── Memory hooks (no-ops unless ENABLE_MEMORY and request.remember) ──────────
def _open_memory(request: AnalysisRequest):
    if not (request.remember and get_settings().enable_memory):
        return None
    try:
        from .memory.service import get_memory_service

        return get_memory_service()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Memory unavailable: %s", exc)
        return None


def _recall_notes(mem, request: AnalysisRequest) -> str:
    try:
        ctx = mem.recall(
            f"Analyze {request.ticker}. {request.notes or ''}",
            user_id=request.user_id,
            ticker=request.ticker,
        )
        return f"PRIOR MEMORY (use for continuity / comparisons):\n{ctx.format()}" if ctx.has_content() else ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("Memory recall failed: %s", exc)
        return ""


def _persist(mem, request: AnalysisRequest, report: InvestmentReport) -> None:
    try:
        mem.add_research_record(
            ticker=report.ticker,
            summary=report.executive_summary,
            recommendation=report.recommendation.value,
            user_id=request.user_id,
            payload={"key_thesis": report.key_thesis, "key_risks": report.key_risks},
        )
        mem.upsert_company_memory(
            report.ticker,
            name=report.company_name,
            sector=report.research.sector,
            notes={"summary": report.executive_summary, "recommendation": report.recommendation.value},
        )
        if request.thread_id:
            mem.add_message(thread_id=request.thread_id, user_id=request.user_id,
                            role="user", content=f"Analyze {report.ticker}")
            mem.add_message(thread_id=request.thread_id, user_id=request.user_id,
                            role="assistant", content=f"{report.recommendation.value}: {report.executive_summary}")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Memory persist failed: %s", exc)

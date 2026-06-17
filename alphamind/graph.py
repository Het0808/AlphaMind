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

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

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
    """Run the full AlphaMind pipeline and return a validated InvestmentReport."""
    graph = get_compiled_graph()
    final_state: AgentState = graph.invoke(
        {
            "ticker": request.ticker.upper(),
            "horizon": request.horizon,
            "notes": request.notes,
            "trace": [],
        }
    )

    synthesis = final_state["synthesis"]
    return InvestmentReport(
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

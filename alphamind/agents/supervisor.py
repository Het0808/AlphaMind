"""Supervisor agent — orchestrator of the AlphaMind crew.

Responsibilities:
  1. `supervisor_plan`  — entry node. Resolves the company and builds the
     research plan that the specialists will execute.
  2. `supervisor_synthesize` — exit node. Reads every specialist report and
     produces the final, decision-grade synthesis (the investment call).
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_llm
from ..schemas import ResearchPlan, Synthesis
from ..state import AgentState
from ..tools import get_company_profile

import logging

logger = logging.getLogger(__name__)

PLANNER_SYSTEM = (
    "You are the Supervisor of AlphaMind, an institutional investment research desk. "
    "Given a company, produce a focused research plan that the specialist team "
    "(research, financial, news, risk) will execute. Be specific and decision-oriented."
)

SYNTH_SYSTEM = (
    "You are the Supervisor of AlphaMind. You have received reports from four "
    "specialists: equity research, financial analysis, news/sentiment, and risk. "
    "Weigh them against each other, resolve conflicts, and issue a single, "
    "decision-grade investment recommendation with explicit conviction. Be "
    "balanced: a strong call requires the financials, narrative, sentiment and "
    "risk to align. State the thesis and the reasons it could be wrong."
)


def supervisor_plan(state: AgentState) -> AgentState:
    """Entry node: resolve the company and draft the research plan."""
    ticker = state["ticker"].upper()
    logger.info("agent=supervisor ticker received: %s", ticker)
    profile = get_company_profile(ticker)
    company_name = profile.get("company_name", ticker)

    llm = get_llm().with_structured_output(ResearchPlan)
    plan: ResearchPlan = llm.invoke(
        [
            SystemMessage(content=PLANNER_SYSTEM),
            HumanMessage(
                content=(
                    f"Company: {company_name} ({ticker})\n"
                    f"Sector: {profile.get('sector')}\n"
                    f"Horizon: {state.get('horizon', '12 months')}\n"
                    f"Analyst notes: {state.get('notes') or 'none'}\n\n"
                    "Draft the research plan."
                )
            ),
        ]
    )

    return {
        "company_name": company_name,
        "plan": plan,
        "trace": [f"supervisor: planned analysis for {company_name} ({ticker})"],
    }


def supervisor_synthesize(state: AgentState) -> AgentState:
    """Exit node: combine all specialist reports into the final call."""
    llm = get_llm().with_structured_output(Synthesis)

    def dump(report) -> str:
        return report.model_dump_json(indent=2) if report else "{}"

    synthesis: Synthesis = llm.invoke(
        [
            SystemMessage(content=SYNTH_SYSTEM),
            HumanMessage(
                content=(
                    f"Company: {state.get('company_name')} ({state['ticker'].upper()})\n"
                    f"Horizon: {state.get('horizon', '12 months')}\n\n"
                    f"=== EQUITY RESEARCH ===\n{dump(state.get('research_report'))}\n\n"
                    f"=== FINANCIAL ANALYSIS ===\n{dump(state.get('financial_report'))}\n\n"
                    f"=== NEWS & SENTIMENT ===\n{dump(state.get('news_report'))}\n\n"
                    f"=== RISK ===\n{dump(state.get('risk_report'))}\n\n"
                    "Issue the final recommendation."
                )
            ),
        ]
    )

    return {
        "synthesis": synthesis,
        "trace": [f"supervisor: final call = {synthesis.recommendation.value} "
                  f"(conviction {synthesis.conviction}/10)"],
    }

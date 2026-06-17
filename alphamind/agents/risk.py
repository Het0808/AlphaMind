"""Risk Agent — downside & risk synthesis.

Unlike the three research specialists, the risk agent runs AFTER them: it reads
their outputs to assess market, financial and business risk holistically, surface
red flags, and assign an overall risk level and 1-10 score.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_llm
from ..schemas import RiskReport
from ..state import AgentState

SYSTEM = (
    "You are the Chief Risk Officer at AlphaMind. Using the research, financial "
    "and news reports, evaluate the investment's risk across three axes — market "
    "risk (volatility/beta/macro), financial risk (leverage/liquidity/earnings "
    "quality), and business risk (competition/execution/regulation). Surface "
    "concrete red flags and assign an overall risk level and a 1-10 risk score "
    "(10 = severe). Be skeptical; your job is to protect capital."
)


def risk_agent(state: AgentState) -> AgentState:
    ticker = state["ticker"].upper()

    def dump(report) -> str:
        return report.model_dump_json(indent=2) if report else "{}"

    llm = get_llm().with_structured_output(RiskReport)
    report: RiskReport = llm.invoke(
        [
            SystemMessage(content=SYSTEM),
            HumanMessage(
                content=(
                    f"Ticker: {ticker}\n\n"
                    f"Research report:\n{dump(state.get('research_report'))}\n\n"
                    f"Financial report:\n{dump(state.get('financial_report'))}\n\n"
                    f"News report:\n{dump(state.get('news_report'))}\n\n"
                    "Write the risk assessment."
                )
            ),
        ]
    )
    return {"risk_report": report, "trace": [f"risk: overall={report.overall_risk.value}"]}

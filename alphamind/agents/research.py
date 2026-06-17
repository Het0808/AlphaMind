"""Research Agent — qualitative equity research.

Covers the business model, competitive moat, growth drivers, threats, and the
bull/bear narrative. Grounds its analysis in a live company profile so it is not
hallucinating the basics.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_llm
from ..schemas import ResearchReport
from ..state import AgentState
from ..tools import get_company_profile

SYSTEM = (
    "You are a senior equity research analyst at AlphaMind. Produce rigorous, "
    "balanced qualitative research on the company: what it does, its economic "
    "moat, structural growth drivers, competitive threats, and a crisp bull and "
    "bear case. Ground every claim in the provided profile and your knowledge; "
    "do not invent precise figures."
)


def research_agent(state: AgentState) -> AgentState:
    ticker = state["ticker"].upper()
    profile = get_company_profile(ticker)

    llm = get_llm().with_structured_output(ResearchReport)
    report: ResearchReport = llm.invoke(
        [
            SystemMessage(content=SYSTEM),
            HumanMessage(
                content=(
                    f"Ticker: {ticker}\n"
                    f"Company profile (live data):\n{profile}\n\n"
                    f"Horizon: {state.get('horizon', '12 months')}\n\n"
                    "Write the equity research report."
                )
            ),
        ]
    )
    return {"research_report": report, "trace": ["research: completed equity research"]}

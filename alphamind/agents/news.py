"""News Agent — news flow & sentiment.

Pulls recent headlines and distills them into an overall sentiment read, the
catalysts that matter, and the individually notable items. Runs at low
temperature to keep sentiment labeling consistent.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_llm
from ..schemas import NewsReport
from ..state import AgentState
from ..tools import get_recent_news

import logging

logger = logging.getLogger(__name__)

SYSTEM = (
    "You are a market-intelligence analyst at AlphaMind. Given recent headlines, "
    "assess the prevailing news sentiment, surface the catalysts (earnings, "
    "products, regulation, management) that could move the stock, and flag the "
    "most material individual items. If no headlines are provided, set sentiment "
    "to NEUTRAL and say coverage is limited rather than inventing news."
)


def news_agent(state: AgentState) -> AgentState:
    ticker = state["ticker"].upper()
    logger.info("agent=news ticker received: %s", ticker)
    headlines = get_recent_news(ticker)

    llm = get_llm(temperature=0.0).with_structured_output(NewsReport)
    report: NewsReport = llm.invoke(
        [
            SystemMessage(content=SYSTEM),
            HumanMessage(
                content=(
                    f"Ticker: {ticker}\n"
                    f"Recent headlines ({len(headlines)} items):\n{headlines}\n\n"
                    "Write the news & sentiment report."
                )
            ),
        ]
    )
    return {"news_report": report, "trace": [f"news: analyzed {len(headlines)} headlines"]}

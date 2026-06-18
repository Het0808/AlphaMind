"""Assemble the debate as a LangGraph and expose `run_debate`.

Topology (multi-round loop, then closings, then judge):

    START → bull → bear ──(more rounds?)──► bull   (loop)
                         └──(done)────────► bull_closing → bear_closing → judge → END

`bull` and `bear` alternate over the shared transcript for `num_rounds` rounds;
the conditional edge after `bear` loops back or proceeds to the closings.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from langgraph.graph import END, START, StateGraph

from ..config import get_settings
from .agents import bear_agent, bear_closing, bull_agent, bull_closing, judge_agent
from .schemas import DebateResult
from .state import DebateState
from .util import should_continue


def _route_after_bear(state: DebateState) -> str:
    return "continue" if should_continue(state["current_round"], state["num_rounds"]) else "closing"


def build_debate_graph():
    g = StateGraph(DebateState)

    g.add_node("bull", bull_agent)
    g.add_node("bear", bear_agent)
    g.add_node("bull_closing", bull_closing)
    g.add_node("bear_closing", bear_closing)
    g.add_node("judge", judge_agent)

    g.add_edge(START, "bull")
    g.add_edge("bull", "bear")
    g.add_conditional_edges("bear", _route_after_bear, {"continue": "bull", "closing": "bull_closing"})
    g.add_edge("bull_closing", "bear_closing")
    g.add_edge("bear_closing", "judge")
    g.add_edge("judge", END)

    return g.compile()


@lru_cache
def get_compiled_debate():
    return build_debate_graph()


def build_briefing(ticker: str) -> tuple[str, str]:
    """Assemble a real-data briefing (and resolve the company name) for the debate."""
    from ..tools import get_financial_snapshot

    snap = get_financial_snapshot(ticker)
    if snap.get("error") or not snap.get("overview"):
        return f"Company ticker: {ticker}. (Live financial data unavailable.)", ticker

    ov, m = snap["overview"], snap.get("metrics", {})
    name = ov.get("name") or ticker
    briefing = (
        f"Company: {name} ({ticker})\n"
        f"Sector: {ov.get('sector')} | Industry: {ov.get('industry')}\n"
        f"Revenue: {m.get('revenue')} | Net income: {m.get('net_income')} | EPS: {m.get('eps')}\n"
        f"Market cap: {m.get('market_cap')} | P/E: {m.get('pe_ratio')}\n"
        f"Operating cash flow: {m.get('operating_cash_flow')} | Free cash flow: {m.get('free_cash_flow')}\n"
        f"Data sources: {', '.join(snap.get('providers_used', [])) or 'n/a'}"
    )
    return briefing, name


def run_debate(ticker: str, *, rounds: Optional[int] = None, context: Optional[str] = None) -> DebateResult:
    """Run the full Bull/Bear/Judge debate for any company and return a DebateResult.

    `ticker` may be a symbol OR a company name (US/India); it is resolved up front.
    """
    from ..resolver import resolve_ticker

    resolution = resolve_ticker(ticker)
    ticker = resolution.ticker
    rounds = rounds or get_settings().debate_rounds

    if context:
        company_name = resolution.company_name
        briefing = context
    else:
        briefing, company_name = build_briefing(ticker)
        company_name = company_name or resolution.company_name

    final: DebateState = get_compiled_debate().invoke(
        {
            "ticker": ticker,
            "company_name": company_name,
            "context": briefing,
            "num_rounds": rounds,
            "current_round": 1,
            "transcript": [],
            "trace": [],
        }
    )

    judge = final["judge"]
    return DebateResult(
        ticker=ticker,
        company_name=final.get("company_name", company_name),
        rounds=rounds,
        bull_thesis=final["bull_thesis"],
        bear_thesis=final["bear_thesis"],
        judge=judge,
        confidence=judge.confidence,
        transcript=final.get("transcript", []),
    )

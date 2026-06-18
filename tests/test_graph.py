"""Structural tests that need no API key — they verify wiring, not LLM output."""

import pytest

# These tests exercise the compiled LangGraph; skip cleanly where langgraph isn't
# installed instead of erroring out and interrupting the whole suite.
pytest.importorskip("langgraph")

from alphamind.graph import build_graph  # noqa: E402
from alphamind.schemas import AnalysisRequest, InvestmentReport  # noqa: E402
from alphamind.state import AgentState  # noqa: E402


def test_graph_compiles_with_expected_nodes():
    graph = build_graph()
    nodes = set(graph.get_graph().nodes)
    for expected in {
        "supervisor_plan",
        "research",
        "financial",
        "news",
        "risk",
        "supervisor_synthesize",
    }:
        assert expected in nodes


def test_request_schema_defaults():
    req = AnalysisRequest(ticker="aapl")
    assert req.ticker == "aapl"
    assert req.horizon == "12 months"


def test_state_is_typeddict():
    # total=False means every key is optional; an empty dict is a valid state.
    s: AgentState = {}
    assert isinstance(s, dict)


def test_investment_report_is_serializable():
    fields = InvestmentReport.model_fields
    for required in {"ticker", "recommendation", "research", "financials", "news", "risk"}:
        assert required in fields

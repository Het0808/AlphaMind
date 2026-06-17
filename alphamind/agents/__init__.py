"""AlphaMind specialist agents.

Each agent is a pure function `(AgentState) -> partial AgentState`. They never
mutate state in place; they return only the keys they own, which keeps the graph
deterministic and parallel-safe.
"""

from .financial import financial_agent
from .news import news_agent
from .research import research_agent
from .risk import risk_agent
from .supervisor import supervisor_plan, supervisor_synthesize

__all__ = [
    "supervisor_plan",
    "supervisor_synthesize",
    "research_agent",
    "financial_agent",
    "news_agent",
    "risk_agent",
]

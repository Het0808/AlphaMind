"""AlphaMind multi-agent debate.

A Bull agent and a Bear agent argue across multiple rounds over a shared memory
(the debate transcript), each producing structured reasoning and confidence
scores. A Judge then evaluates both sides and renders a decision with a calibrated
confidence.

Only `schemas` is imported eagerly so `import alphamind.debate` stays light; the
graph (which needs LangGraph) is imported from `alphamind.debate.graph`.
"""

from .schemas import (
    ArgumentContent,
    DebateArgument,
    DebateResult,
    JudgeDecision,
    SideThesis,
)

__all__ = [
    "ArgumentContent",
    "DebateArgument",
    "SideThesis",
    "JudgeDecision",
    "DebateResult",
]

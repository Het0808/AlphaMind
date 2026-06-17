"""Debate graph state — the shared memory both agents read and write.

`transcript` is the shared memory: an append-only log (additive reducer) of every
argument made so far. On each turn an agent reads the whole transcript before
speaking, so the debate genuinely builds round over round.
"""

from __future__ import annotations

from operator import add
from typing import Annotated, List, Optional

from typing_extensions import TypedDict

from .schemas import DebateArgument, JudgeDecision, SideThesis


class DebateState(TypedDict, total=False):
    # ── Inputs ──
    ticker: str
    company_name: str
    context: str            # shared briefing (real financials etc.) given to both sides
    num_rounds: int
    current_round: int

    # ── Shared memory ──
    transcript: Annotated[List[DebateArgument], add]

    # ── Closings + verdict ──
    bull_thesis: Optional[SideThesis]
    bear_thesis: Optional[SideThesis]
    judge: Optional[JudgeDecision]

    # ── Observability ──
    trace: Annotated[List[str], add]

"""Structured contracts for the debate: arguments, theses, and the judge's ruling.

`ArgumentContent` / `ThesisContent` are what the LLM is forced to emit; the
`stance`/`round` provenance is attached in code, so the model focuses purely on
reasoning. Every artifact carries an explicit 1-10 confidence score.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal

from pydantic import BaseModel, Field

from ..schemas import Recommendation

Stance = Literal["bull", "bear"]


# ── What each debating agent emits per round (structured reasoning) ──
class ArgumentContent(BaseModel):
    claims: List[str] = Field(..., description="Distinct, load-bearing claims made this round.")
    rebuttals: List[str] = Field(default_factory=list, description="Direct responses to the opponent's latest points.")
    evidence: List[str] = Field(default_factory=list, description="Specific facts/figures cited in support.")
    confidence: int = Field(..., ge=1, le=10, description="Strength of this round's case, 1-10.")
    summary: str = Field(..., description="One-line summary of the round's thrust.")


class DebateArgument(ArgumentContent):
    round: int
    stance: Stance


# ── Each side's consolidated closing thesis ──
class ThesisContent(BaseModel):
    thesis: str = Field(..., description="The single strongest consolidated thesis statement.")
    key_points: List[str] = Field(..., description="The pillars supporting the thesis.")
    strongest_point: str = Field(..., description="The most decisive single argument.")
    acknowledged_weaknesses: List[str] = Field(default_factory=list, description="Honest concessions.")
    confidence: int = Field(..., ge=1, le=10)


class SideThesis(ThesisContent):
    stance: Stance


# ── The judge's evaluation ──
class JudgeDecision(BaseModel):
    winner: Literal["bull", "bear", "tie"]
    recommendation: Recommendation
    confidence: int = Field(..., ge=1, le=10, description="Calibrated confidence in the decision.")
    bull_score: int = Field(..., ge=1, le=10, description="Quality of the bull case.")
    bear_score: int = Field(..., ge=1, le=10, description="Quality of the bear case.")
    reasoning: str = Field(..., description="How the decision was reached (logic & evidence, not rhetoric).")
    decisive_argument: str = Field(..., description="The argument that tipped the balance.")
    key_factors: List[str] = Field(..., description="Factors that most influenced the verdict.")


# ── Final aggregated result ──
class DebateResult(BaseModel):
    ticker: str
    company_name: str
    rounds: int
    bull_thesis: SideThesis
    bear_thesis: SideThesis
    judge: JudgeDecision
    confidence: int = Field(..., ge=1, le=10, description="Convenience mirror of judge.confidence.")
    transcript: List[DebateArgument] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

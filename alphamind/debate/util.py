"""Pure, dependency-light helpers for the debate (no LangChain/LangGraph imports).

Kept separate so the round-control and transcript-rendering logic is unit-testable
without the heavy LLM/graph dependencies.
"""

from __future__ import annotations

from typing import List

from .schemas import DebateArgument


def should_continue(current_round: int, num_rounds: int) -> bool:
    """True while another full Bull/Bear round remains to be debated."""
    return current_round <= num_rounds


def render_transcript(transcript: List[DebateArgument], *, last_n: int | None = None) -> str:
    """Render the shared memory into a prompt-friendly transcript."""
    if not transcript:
        return "(no prior arguments — this is the opening round)"
    items = transcript[-last_n:] if last_n else transcript
    lines: List[str] = []
    for arg in items:
        lines.append(f"[Round {arg.round} • {arg.stance.upper()} — confidence {arg.confidence}/10]")
        lines.append("  Claims: " + " | ".join(arg.claims))
        if arg.rebuttals:
            lines.append("  Rebuttals: " + " | ".join(arg.rebuttals))
        if arg.evidence:
            lines.append("  Evidence: " + " | ".join(arg.evidence))
    return "\n".join(lines)


def latest_opponent_points(transcript: List[DebateArgument], opponent: str) -> str:
    """The opponent's most recent argument, for targeted rebuttal."""
    for arg in reversed(transcript):
        if arg.stance == opponent:
            return " | ".join(arg.claims)
    return "(opponent has not spoken yet)"

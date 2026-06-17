"""The three debate agents: Bull, Bear, and Judge (plus the closing-statement steps).

Bull and Bear each run once per round, reading the full shared transcript before
arguing and rebutting. After the final round each delivers a consolidated closing
thesis. The Judge then evaluates the whole debate and both theses.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import get_llm
from .schemas import (
    ArgumentContent,
    DebateArgument,
    JudgeDecision,
    SideThesis,
    ThesisContent,
)
from .state import DebateState
from .util import latest_opponent_points, render_transcript

_BULL_SYSTEM = (
    "You are the BULL in a structured investment debate. Make the strongest, "
    "intellectually honest case FOR investing in the company. Use the real "
    "financials in the briefing and cite specific figures. Each round, advance "
    "NEW arguments and directly rebut the Bear's latest points — do not repeat "
    "yourself. Provide distinct claims, targeted rebuttals, concrete evidence, "
    "and an honest 1-10 confidence."
)
_BEAR_SYSTEM = (
    "You are the BEAR in a structured investment debate. Make the strongest, "
    "intellectually honest case AGAINST investing in the company. Use the real "
    "financials in the briefing and cite specific figures. Each round, advance "
    "NEW arguments and directly rebut the Bull's latest points — do not repeat "
    "yourself. Provide distinct claims, targeted rebuttals, concrete evidence, "
    "and an honest 1-10 confidence."
)
_CLOSING_SYSTEM = (
    "The debate has concluded. As the {side}, synthesize your single strongest "
    "consolidated thesis from your arguments across all rounds. Be honest: "
    "acknowledge your real weaknesses. Give the key points, your single strongest "
    "point, and an overall 1-10 confidence."
)
_JUDGE_SYSTEM = (
    "You are an impartial portfolio manager judging an investment debate. Evaluate "
    "the full transcript and both closing theses on logic, evidence quality and "
    "risk-adjusted merit — NOT rhetoric or confidence theatrics. Score each side "
    "1-10, name a winner (or 'tie'), issue an investment recommendation, give a "
    "calibrated 1-10 confidence, and explain the decisive factors. Penalize "
    "unsupported claims on either side."
)


def _round_prompt(stance: str, state: DebateState) -> str:
    transcript = state.get("transcript", [])
    opponent = "bear" if stance == "bull" else "bull"
    return (
        f"BRIEFING:\n{state.get('context', '')}\n\n"
        f"DEBATE SO FAR (shared memory):\n{render_transcript(transcript)}\n\n"
        f"Opponent's latest points to rebut: {latest_opponent_points(transcript, opponent)}\n\n"
        f"This is round {state['current_round']}. Make your {stance.upper()} argument."
    )


def bull_agent(state: DebateState) -> DebateState:
    draft: ArgumentContent = get_llm().with_structured_output(ArgumentContent).invoke(
        [SystemMessage(content=_BULL_SYSTEM), HumanMessage(content=_round_prompt("bull", state))]
    )
    arg = DebateArgument(round=state["current_round"], stance="bull", **draft.model_dump())
    return {"transcript": [arg], "trace": [f"bull: round {arg.round} (conf {arg.confidence}/10)"]}


def bear_agent(state: DebateState) -> DebateState:
    draft: ArgumentContent = get_llm().with_structured_output(ArgumentContent).invoke(
        [SystemMessage(content=_BEAR_SYSTEM), HumanMessage(content=_round_prompt("bear", state))]
    )
    arg = DebateArgument(round=state["current_round"], stance="bear", **draft.model_dump())
    # Bear closes the round → advance the round counter.
    return {
        "transcript": [arg],
        "current_round": state["current_round"] + 1,
        "trace": [f"bear: round {arg.round} (conf {arg.confidence}/10)"],
    }


def _closing(stance: str, state: DebateState) -> SideThesis:
    own = [a for a in state.get("transcript", []) if a.stance == stance]
    draft: ThesisContent = get_llm().with_structured_output(ThesisContent).invoke(
        [
            SystemMessage(content=_CLOSING_SYSTEM.format(side=stance.upper())),
            HumanMessage(
                content=(
                    f"BRIEFING:\n{state.get('context', '')}\n\n"
                    f"Your arguments across the debate:\n{render_transcript(own)}\n\n"
                    f"Deliver your consolidated {stance.upper()} closing thesis."
                )
            ),
        ]
    )
    return SideThesis(stance=stance, **draft.model_dump())


def bull_closing(state: DebateState) -> DebateState:
    return {"bull_thesis": _closing("bull", state), "trace": ["bull: closing thesis"]}


def bear_closing(state: DebateState) -> DebateState:
    return {"bear_thesis": _closing("bear", state), "trace": ["bear: closing thesis"]}


def judge_agent(state: DebateState) -> DebateState:
    bull = state["bull_thesis"]
    bear = state["bear_thesis"]
    decision: JudgeDecision = get_llm(temperature=0.0).with_structured_output(JudgeDecision).invoke(
        [
            SystemMessage(content=_JUDGE_SYSTEM),
            HumanMessage(
                content=(
                    f"BRIEFING:\n{state.get('context', '')}\n\n"
                    f"FULL DEBATE TRANSCRIPT:\n{render_transcript(state.get('transcript', []))}\n\n"
                    f"BULL CLOSING THESIS:\n{bull.model_dump_json(indent=2)}\n\n"
                    f"BEAR CLOSING THESIS:\n{bear.model_dump_json(indent=2)}\n\n"
                    "Render your verdict."
                )
            ),
        ]
    )
    return {
        "judge": decision,
        "trace": [f"judge: winner={decision.winner}, {decision.recommendation.value} "
                  f"(conf {decision.confidence}/10)"],
    }

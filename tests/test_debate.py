"""Offline tests for the debate's pure logic and schemas (no LLM / LangGraph)."""

import pytest
from pydantic import ValidationError

from alphamind.debate.schemas import (
    ArgumentContent,
    DebateArgument,
    DebateResult,
    JudgeDecision,
    SideThesis,
)
from alphamind.debate.util import (
    latest_opponent_points,
    render_transcript,
    should_continue,
)


def _arg(stance, rnd, claim):
    return DebateArgument(
        round=rnd, stance=stance, claims=[claim], rebuttals=[], evidence=[],
        confidence=7, summary="x",
    )


@pytest.mark.parametrize(
    "current,total,expected",
    [(1, 2, True), (2, 2, True), (3, 2, False), (1, 1, True), (2, 1, False)],
)
def test_should_continue_round_control(current, total, expected):
    assert should_continue(current, total) is expected


def test_render_transcript_empty_and_full():
    assert "opening round" in render_transcript([])
    text = render_transcript([_arg("bull", 1, "great margins"), _arg("bear", 1, "rich valuation")])
    assert "BULL" in text and "BEAR" in text
    assert "great margins" in text and "rich valuation" in text


def test_latest_opponent_points_picks_most_recent():
    transcript = [_arg("bear", 1, "old bear point"), _arg("bear", 2, "new bear point")]
    assert latest_opponent_points(transcript, "bear") == "new bear point"
    assert "not spoken" in latest_opponent_points([], "bull")


def test_argument_confidence_bounds():
    with pytest.raises(ValidationError):
        ArgumentContent(claims=["c"], confidence=11, summary="s")


def test_debate_result_assembles_and_mirrors_confidence():
    bull = SideThesis(stance="bull", thesis="buy", key_points=["a"], strongest_point="a", confidence=8)
    bear = SideThesis(stance="bear", thesis="avoid", key_points=["b"], strongest_point="b", confidence=6)
    judge = JudgeDecision(
        winner="bull", recommendation="BUY", confidence=7, bull_score=8, bear_score=6,
        reasoning="bull better supported", decisive_argument="cash flow", key_factors=["fcf"],
    )
    result = DebateResult(
        ticker="AAPL", company_name="Apple Inc.", rounds=2,
        bull_thesis=bull, bear_thesis=bear, judge=judge, confidence=judge.confidence,
    )
    assert result.confidence == 7
    assert result.judge.winner == "bull"
    assert result.bull_thesis.stance == "bull" and result.bear_thesis.stance == "bear"


def test_judge_winner_is_constrained():
    with pytest.raises(ValidationError):
        JudgeDecision(
            winner="nobody", recommendation="HOLD", confidence=5, bull_score=5, bear_score=5,
            reasoning="r", decisive_argument="d", key_factors=["k"],
        )

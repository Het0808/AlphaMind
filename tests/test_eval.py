"""Offline tests for the evaluation framework (deterministic metric cores)."""

from alphamind.eval.metrics import (
    Faithfulness,
    HallucinationRate,
    ResponseCompleteness,
    RetrievalQuality,
    ToolUsageAccuracy,
    claim_support,
    coverage,
    tokenize,
)
from alphamind.eval.report import build_report
from alphamind.eval.runner import EvaluationRunner
from alphamind.eval.schemas import AgentOutput, EvalSample


# ── helpers ──
def test_tokenize_and_coverage():
    assert "revenue" in tokenize("Revenue grew strongly")
    assert "the" not in tokenize("the revenue")  # stopword removed
    assert coverage({"a", "b"}, {"a", "b", "c"}) == 1.0
    assert coverage({"a", "b"}, {"a"}) == 0.5


# ── Faithfulness / Hallucination ──
def test_faithfulness_supported_vs_unsupported():
    ctx = ["NVIDIA relies on TSMC for chip manufacturing and faces export controls."]
    grounded = AgentOutput(answer="NVIDIA relies on TSMC. It faces export controls.")
    hallucinated = AgentOutput(answer="NVIDIA owns gold mines on Mars.")

    f = Faithfulness(0.7)
    s = EvalSample(id="x", question="q", contexts=ctx)
    assert f.evaluate(s, grounded).score == 1.0
    assert f.evaluate(s, grounded).passed
    assert f.evaluate(s, hallucinated).score < 0.5


def test_hallucination_rate_direction():
    s = EvalSample(id="x", question="q", contexts=["Apple revenue was strong."])
    h = HallucinationRate(0.2)
    bad = h.evaluate(s, AgentOutput(answer="Apple builds submarines in Antarctica."))
    assert bad.score > 0.5 and bad.passed is False
    assert bad.higher_is_better is False


def test_faithfulness_skipped_without_context():
    res = Faithfulness().evaluate(EvalSample(id="x", question="q"), AgentOutput(answer="anything"))
    assert res.skipped and res.passed


# ── Retrieval quality ──
def test_retrieval_quality_precision_recall():
    s = EvalSample(id="x", question="q",
                   reference_contexts=["TSMC manufacturing risk", "export control risk"])
    out = AgentOutput(contexts=["TSMC manufacturing risk concentration", "irrelevant cooking recipe"])
    res = RetrievalQuality(0.5).evaluate(s, out)
    assert 0 < res.score < 1
    assert res.breakdown["precision"] == 0.5  # 1 of 2 retrieved is relevant


def test_retrieval_quality_skipped_without_gold():
    res = RetrievalQuality().evaluate(EvalSample(id="x", question="q"), AgentOutput(contexts=["a"]))
    assert res.skipped


# ── Tool usage ──
def test_tool_usage_accuracy_f1():
    s = EvalSample(id="x", question="q", expected_tools=["get_financial_snapshot", "search_filings"])
    res = ToolUsageAccuracy(0.7).evaluate(s, AgentOutput(tool_calls=["get_financial_snapshot"]))
    assert res.breakdown["recall"] == 0.5
    assert res.breakdown["missing"] == ["search_filings"]
    perfect = ToolUsageAccuracy(0.7).evaluate(
        s, AgentOutput(tool_calls=["get_financial_snapshot", "search_filings"]))
    assert perfect.score == 1.0 and perfect.passed


# ── Completeness ──
def test_response_completeness_coverage():
    s = EvalSample(id="x", question="q", required_points=["revenue", "net income", "cash flow"])
    res = ResponseCompleteness(0.7).evaluate(
        s, AgentOutput(answer="Revenue rose and net income grew."))
    assert abs(res.score - 2 / 3) < 1e-3  # scores are rounded to 4 dp
    assert res.breakdown["missing"] == ["cash flow"]


# ── Report aggregation + failure analysis ──
def test_build_report_aggregates_and_collects_failures():
    runner = EvaluationRunner()
    good = EvalSample(id="g", agent="research", question="q",
                      contexts=["TSMC risk and export controls"],
                      expected_tools=["search_filings"], required_points=["TSMC"])
    bad = EvalSample(id="b", agent="research", question="q",
                     contexts=["TSMC risk"], expected_tools=["search_filings"],
                     required_points=["TSMC"])

    outputs = {
        "g": AgentOutput(answer="TSMC risk and export controls.", tool_calls=["search_filings"]),
        "b": AgentOutput(answer="Bananas are yellow.", tool_calls=["wrong_tool"]),
    }
    report = runner.run([good, bad], lambda s: outputs[s.id], run_id="t1")

    assert report.run_id == "t1" and report.n_samples == 2
    assert "faithfulness" in report.metric_averages
    assert 0.0 <= report.overall_quality <= 1.0
    # The bad sample should have failures recorded with reasons.
    assert any(f.sample_id == "b" for f in report.failures)
    assert "research" in report.agent_breakdown

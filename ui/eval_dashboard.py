"""AlphaMind — Evaluation dashboard.

Visualizes an EvalReport: agent performance, evaluation scores, and failure
analysis. Generate a report first, then point the dashboard at it:

    python -m alphamind.eval.run --outputs outputs.json --out eval_report.json
    streamlit run ui/eval_dashboard.py
"""

from __future__ import annotations

import json
import os

import pandas as pd
import streamlit as st

st.set_page_config(page_title="AlphaMind Eval", page_icon="📊", layout="wide")
st.title("📊 AlphaMind — LLM Evaluation Dashboard")

default_path = os.getenv("EVAL_REPORT_PATH", "eval_report.json")
with st.sidebar:
    st.header("Report")
    path = st.text_input("Report JSON path", value=default_path)
    uploaded = st.file_uploader("…or upload a report", type="json")

if uploaded is not None:
    report = json.load(uploaded)
elif path and os.path.exists(path):
    with open(path) as f:
        report = json.load(f)
else:
    st.info("Provide an eval_report.json (run `python -m alphamind.eval.run`).")
    st.stop()

# ── Headline ──
c1, c2, c3 = st.columns(3)
c1.metric("Overall quality", f"{report.get('overall_quality', 0):.0%}")
c2.metric("Samples", report.get("n_samples", 0))
c3.metric("Failures", len(report.get("failures", [])))

# ── Evaluation scores ──
st.subheader("Evaluation scores")
averages = report.get("metric_averages", {})
pass_rates = report.get("pass_rates", {})
if averages:
    score_df = pd.DataFrame(
        {"metric": list(averages.keys()),
         "average": list(averages.values()),
         "pass_rate": [pass_rates.get(m, float("nan")) for m in averages]}
    ).set_index("metric")
    a, b = st.columns(2)
    with a:
        st.caption("Average score")
        st.bar_chart(score_df["average"])
    with b:
        st.caption("Pass rate")
        st.bar_chart(score_df["pass_rate"])
    st.dataframe(score_df.style.format("{:.2%}"), use_container_width=True)

# ── Agent performance ──
st.subheader("Agent performance")
breakdown = report.get("agent_breakdown", {})
if breakdown:
    agent_df = pd.DataFrame(breakdown).T  # agents as rows, metrics as columns
    st.dataframe(agent_df.style.format("{:.2%}", na_rep="—"), use_container_width=True)
    st.bar_chart(agent_df)
else:
    st.caption("No per-agent breakdown in this report.")

# ── Failure analysis ──
st.subheader("Failure analysis")
failures = report.get("failures", [])
if failures:
    fdf = pd.DataFrame(failures)
    metrics = ["(all)"] + sorted(fdf["metric"].unique().tolist())
    chosen = st.selectbox("Filter by metric", metrics)
    if chosen != "(all)":
        fdf = fdf[fdf["metric"] == chosen]
    st.dataframe(fdf[["sample_id", "agent", "metric", "score", "reason", "question"]],
                 use_container_width=True)
    st.caption("Failures by metric")
    st.bar_chart(pd.DataFrame(failures)["metric"].value_counts())
else:
    st.success("No failures 🎉")

# ── Per-sample drill-down ──
with st.expander("Per-sample results"):
    for res in report.get("results", []):
        flagged = ", ".join(res.get("failed_metrics", [])) or "all passed"
        st.markdown(f"**{res['sample_id']}** ({res.get('agent') or '—'}) — {flagged}")
        st.caption(res["question"])
        st.dataframe(pd.DataFrame(res["scores"])[["metric", "score", "passed", "skipped", "detail"]],
                     use_container_width=True)

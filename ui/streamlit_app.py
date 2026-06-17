"""AlphaMind — Streamlit analyst console.

A thin client over the FastAPI `/analyze` endpoint. Run the API first, then:

    streamlit run ui/streamlit_app.py
"""

from __future__ import annotations

import os

import httpx
import streamlit as st

API_URL = os.getenv("ALPHAMIND_API_URL", "http://localhost:8000")

st.set_page_config(page_title="AlphaMind", page_icon="📈", layout="wide")

st.title("📈 AlphaMind")
st.caption("Agentic AI Investment Research — Supervisor • Research • Financial • News • Risk")

with st.sidebar:
    st.header("Analysis")
    ticker = st.text_input("Ticker", value="AAPL").strip().upper()
    horizon = st.selectbox("Horizon", ["3 months", "12 months", "3 years", "5 years"], index=1)
    notes = st.text_area("Analyst notes (optional)", placeholder="e.g. focus on AI exposure")
    run = st.button("Run analysis", type="primary", use_container_width=True)

    with st.expander("Connection"):
        st.write(f"API: `{API_URL}`")
        try:
            h = httpx.get(f"{API_URL}/health", timeout=5).json()
            st.success(f"Online · model {h.get('model')} · key {'✅' if h.get('openai_configured') else '❌'}")
        except Exception as exc:  # noqa: BLE001
            st.error(f"API unreachable: {exc}")


def _rec_color(rec: str) -> str:
    return {
        "STRONG_BUY": "🟢", "BUY": "🟢", "HOLD": "🟡",
        "SELL": "🔴", "STRONG_SELL": "🔴",
    }.get(rec, "⚪️")


if run and ticker:
    with st.spinner(f"AlphaMind crew analyzing {ticker}…"):
        try:
            resp = httpx.post(
                f"{API_URL}/analyze",
                json={"ticker": ticker, "horizon": horizon, "notes": notes or None},
                timeout=180,
            )
            resp.raise_for_status()
            report = resp.json()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Analysis failed: {exc}")
            st.stop()

    # ── Headline ──
    st.subheader(f"{report['company_name']} ({report['ticker']})")
    c1, c2, c3 = st.columns(3)
    c1.metric("Recommendation", f"{_rec_color(report['recommendation'])} {report['recommendation']}")
    c2.metric("Conviction", f"{report['conviction']}/10")
    c3.metric("Risk", f"{report['risk']['overall_risk']} ({report['risk']['risk_score']}/10)")

    st.info(report["executive_summary"])

    t1, t2 = st.columns(2)
    with t1:
        st.markdown("**✅ Thesis**")
        for item in report["key_thesis"]:
            st.markdown(f"- {item}")
    with t2:
        st.markdown("**⚠️ Key risks**")
        for item in report["key_risks"]:
            st.markdown(f"- {item}")

    # ── Specialist tabs ──
    tabs = st.tabs(["🔬 Research", "💰 Financials", "📰 News", "🛡️ Risk", "🧾 Raw JSON"])

    with tabs[0]:
        r = report["research"]
        st.markdown(f"**Sector:** {r['sector']}")
        st.markdown(f"**Business:** {r['business_summary']}")
        st.markdown(f"**Moat:** {r['moat']}")
        st.markdown("**Growth drivers:**")
        for g in r["growth_drivers"]:
            st.markdown(f"- {g}")
        st.markdown("**Threats:**")
        for g in r["competitive_threats"]:
            st.markdown(f"- {g}")
        ca, cb = st.columns(2)
        ca.success(f"**Bull case**\n\n{r['bull_case']}")
        cb.warning(f"**Bear case**\n\n{r['bear_case']}")

    with tabs[1]:
        f = report["financials"]
        st.metric("Financial health", f"{f['financial_health_score']}/10")
        st.markdown(f"**Valuation:** {f['valuation_summary']}")
        st.markdown(f"**Profitability:** {f['profitability']}")
        st.markdown(f"**Balance sheet:** {f['balance_sheet']}")
        st.markdown(f"**Growth:** {f['growth_trend']}")
        if f.get("key_metrics"):
            st.json(f["key_metrics"])

    with tabs[2]:
        n = report["news"]
        st.markdown(f"**Overall sentiment:** {n['overall_sentiment']}")
        st.markdown(f"{n['summary']}")
        st.markdown("**Catalysts:**")
        for c in n["catalysts"]:
            st.markdown(f"- {c}")
        for item in n.get("notable_items", []):
            st.markdown(f"- *{item['sentiment']}* — {item['headline']} ({item['relevance']})")

    with tabs[3]:
        rk = report["risk"]
        st.markdown(f"**Overall risk:** {rk['overall_risk']} ({rk['risk_score']}/10)")
        st.markdown(f"**Market risk:** {rk['market_risk']}")
        st.markdown(f"**Financial risk:** {rk['financial_risk']}")
        st.markdown(f"**Business risk:** {rk['business_risk']}")
        if rk.get("red_flags"):
            st.markdown("**🚩 Red flags:**")
            for rf in rk["red_flags"]:
                st.markdown(f"- {rf}")

    with tabs[4]:
        st.json(report)

elif run:
    st.warning("Enter a ticker first.")

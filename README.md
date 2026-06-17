# 📈 AlphaMind

**Agentic AI Investment Research Platform** — a supervisor-orchestrated crew of
specialist agents that turn a single ticker into a decision-grade, fully
structured investment report.

Built with **LangGraph · FastAPI · Streamlit · OpenAI · Pydantic**.

---

## ✨ What it does

Give it a ticker (e.g. `AAPL`). A **Supervisor** agent plans the work and
dispatches four specialists that run as a graph:

| Agent | Role | Output |
|-------|------|--------|
| 🧭 **Supervisor** | Plans the analysis, then synthesizes the final call | `ResearchPlan`, `Synthesis` |
| 🔬 **Research** | Business model, moat, growth drivers, bull/bear case | `ResearchReport` |
| 💰 **Financial** | Valuation, profitability, balance sheet, growth | `FinancialReport` |
| 📰 **News** | Headline flow, sentiment, catalysts | `NewsReport` |
| 🛡️ **Risk** | Market / financial / business risk, red flags | `RiskReport` |

Every agent emits a **validated Pydantic model** — never free text — and the API
returns one aggregated, JSON-serializable `InvestmentReport`.

---

## 🏗️ Architecture

```
                          ┌──────────────────────┐
                          │     Streamlit UI      │  ui/streamlit_app.py
                          │   (analyst console)   │
                          └───────────┬───────────┘
                                      │ HTTP (POST /analyze)
                          ┌───────────▼───────────┐
                          │      FastAPI API       │  api/main.py
                          │   /health   /analyze   │
                          └───────────┬───────────┘
                                      │ analyze(request)
                          ┌───────────▼───────────┐
                          │   LangGraph pipeline   │  alphamind/graph.py
                          └───────────┬───────────┘
                                      │
                                  ┌───▼────────────────┐
                                  │  supervisor_plan   │  (resolve company, plan)
                                  └───┬───────┬───────┬┘
                  ┌───────────────────┘       │       └───────────────────┐
                  ▼                           ▼                           ▼
          ┌──────────────┐           ┌──────────────┐            ┌──────────────┐
          │   research   │           │  financial   │            │     news     │   ← parallel fan-out
          └───────┬──────┘           └───────┬──────┘            └───────┬──────┘
                  └──────────────────────────┼──────────────────────────┘
                                             ▼
                                      ┌──────────────┐
                                      │     risk     │   ← fan-in (waits for all 3)
                                      └───────┬──────┘
                                             ▼
                                  ┌──────────────────────┐
                                  │ supervisor_synthesize │   → InvestmentReport (JSON)
                                  └──────────────────────┘

   Tools layer (alphamind/tools): market_data (yfinance) · news_feed
   Shared state (alphamind/state.py): typed, per-agent keys, additive trace reducer
```

**Why this topology?** The three research specialists are independent, so they
**fan out in parallel** (each writes its own state key → no write conflicts). The
risk agent depends on all three, so it **fans in** (LangGraph waits for every
inbound edge). The supervisor bookends the graph: plan first, synthesize last.

---

## 📊 Real financial data layer

`alphamind/data/` pulls **real** fundamentals for any public ticker and merges
them across three sources, so no single provider is a point of failure:

| Source | Strengths | Needs key? |
|--------|-----------|-----------|
| **Yahoo Finance** | Live market cap, trailing PE/EPS, broad profile | No |
| **SEC EDGAR** | Authoritative, audited 10-K fundamentals (revenue, net income, EPS, cash flow) | No (UA only) |
| **Financial Modeling Prep** | Clean, normalized statements + market data | Yes (free tier) |

**Returned metrics:** company overview · revenue · net income · EPS · market cap ·
PE ratio · operating & free cash flow — as a validated `FinancialSnapshot`.

```python
from alphamind.data import get_financial_service

snap = get_financial_service().get_snapshot("AAPL")
print(snap.metrics.revenue, snap.metrics.eps, snap.metrics.market_cap)
print(snap.providers_used)      # e.g. ['fmp', 'sec_edgar', 'yahoo']
print(snap.field_sources)       # which provider supplied each field
```

**How it works**
- **Merge + provenance** — fields fill by priority (FMP → Yahoo → EDGAR); the
  first valid value wins and `field_sources` records where each came from.
- **Validation** — Pydantic models reject non-finite numbers; NaN/inf from one
  provider is treated as *missing* so a healthy value can backfill it.
- **Error handling** — typed exceptions (`TickerNotFound`, `RateLimited`,
  `ProviderUnavailable`, `MissingCredentials`); one provider failing only adds a
  warning, it never aborts the request.
- **Caching** — each snapshot is cached per-ticker for `DATA_CACHE_TTL` seconds
  (EDGAR's CIK map and company-facts are cached too) to cut latency, cost and
  rate-limit risk.

> ℹ️ EDGAR requires a descriptive `SEC_USER_AGENT` with a real contact email.
> Without an `FMP_API_KEY`, FMP self-disables and Yahoo + EDGAR carry the load.

## 📁 Project structure

```
ALphA_MinDs/
├── README.md
├── requirements.txt
├── .env.example                # copy to .env
├── .gitignore
├── Makefile                    # make install | api | ui | test
│
├── alphamind/                  # core package
│   ├── config.py               # pydantic-settings (typed env config)
│   ├── llm.py                  # single ChatOpenAI factory
│   ├── schemas.py              # all Pydantic I/O contracts
│   ├── state.py                # LangGraph shared state (TypedDict + reducers)
│   ├── graph.py                # graph assembly + analyze() entrypoint
│   ├── agents/
│   │   ├── supervisor.py       # plan + synthesize
│   │   ├── research.py
│   │   ├── financial.py
│   │   ├── news.py
│   │   └── risk.py
│   ├── data/                   # ── real financial data layer ──
│   │   ├── service.py          # FinancialDataService (merge + validate + cache)
│   │   ├── schemas.py          # CompanyOverview / FinancialMetrics / Snapshot
│   │   ├── cache.py            # thread-safe TTL cache
│   │   ├── exceptions.py       # typed provider errors
│   │   └── providers/
│   │       ├── yahoo.py        # Yahoo Finance (yfinance)
│   │       ├── edgar.py        # SEC EDGAR XBRL API
│   │       └── fmp.py          # Financial Modeling Prep
│   └── tools/
│       ├── financials.py       # tool wrappers over FinancialDataService
│       ├── market_data.py      # legacy yfinance helpers
│       └── news_feed.py        # recent headlines
│
├── api/
│   └── main.py                 # FastAPI app (/health, /analyze)
│
├── ui/
│   └── streamlit_app.py        # analyst console
│
└── tests/
    └── test_graph.py           # structural tests (no API key needed)
```

---

## 🚀 Quickstart

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # or: make install

# 2. Configure
cp .env.example .env                    # then add your OPENAI_API_KEY

# 3. Run the API
make api                                # http://localhost:8000/docs

# 4. Run the UI (separate terminal)
make ui                                 # http://localhost:8501
```

### Call the API directly

```bash
curl -s -X POST http://localhost:8000/analyze \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"AAPL","horizon":"12 months"}' | jq
```

### Or use the graph in Python

```python
from alphamind.graph import analyze
from alphamind.schemas import AnalysisRequest

report = analyze(AnalysisRequest(ticker="AAPL"))
print(report.model_dump_json(indent=2))
```

---

## 🧪 Tests

```bash
make test     # structural tests run without an OpenAI key
```

---

## 🛡️ Best practices baked in

- **Structured outputs everywhere.** Agents use `with_structured_output(Model)`
  so every result is a validated Pydantic object — no brittle string parsing.
- **Single config source.** `pydantic-settings` validates all env vars at
  startup; nothing reads `os.environ` ad-hoc.
- **One LLM factory.** Model, temperature, timeout and retries are configured in
  `llm.py` only — swap models in one place.
- **Parallel-safe state.** Each agent owns a distinct state key; the shared
  `trace` uses an additive reducer so concurrent writes never clobber.
- **Resilient tools.** Data tools degrade gracefully (return `{"error": ...}`)
  instead of crashing the graph when a provider is down.
- **Stateless pure-function agents.** `(state) -> partial state` keeps the graph
  deterministic, testable and easy to reason about.
- **Separation of concerns.** Orchestration (`graph`), reasoning (`agents`),
  data (`tools`), contracts (`schemas`), transport (`api`/`ui`) are decoupled.
- **Secrets stay out of git.** `.env` is gitignored; only `.env.example` ships.

### Recommended next steps for production

- Add **LangSmith** tracing (`LANGCHAIN_TRACING_V2=true`) for full observability.
- Add a **persistence checkpointer** (e.g. Postgres) for resumable, auditable runs.
- Swap `news_feed` for a dedicated provider (NewsAPI / Finnhub) + add a real
  vector-store research tool (RAG over filings & transcripts).
- Add **auth + rate limiting** to the API and pin CORS to your UI origin.
- Add **caching** of tool calls and a **cost/latency budget** per run.

---

> ⚠️ AlphaMind is a research-assistance tool, not financial advice. Outputs are
> AI-generated and must be independently verified before any investment decision.
```

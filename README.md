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

## 📚 RAG over SEC filings (LangChain · Qdrant · OpenAI embeddings)

`alphamind/rag/` builds a retrieval-augmented pipeline over primary-source SEC
filings so the agents can ground claims in — and cite — the actual 10-K/10-Q text.

**Pipeline:** download (EDGAR) → parse 10-K/10-Q → extract **Item 1A Risk Factors**
and **MD&A** → chunk → OpenAI embeddings → **Qdrant** → filtered retrieval →
**exact filing citations**.

```bash
# Ingest filings into Qdrant (defaults to in-memory; set QDRANT_URL/PATH to persist)
python -m alphamind.rag.ingest AAPL MSFT --forms 10-K 10-Q --limit 2
```

```python
from alphamind.rag.retriever import FilingRetriever

ans = FilingRetriever().answer("What are the company's main supply-chain risks?", ticker="AAPL")
print(ans.answer)                      # inline [1], [2] … citations
for c in ans.citations:
    print(c.reference(), "—", c.url)   # AAPL 10-K filed 2025-10-31 (accession ...), Item 1A Risk Factors
```

**API endpoints:** `POST /filings/ingest`, `POST /filings/search`, `POST /filings/qa`.

**Design notes**
- **Robust section extraction** — item headers also appear in the table of
  contents, so the parser keeps the *longest* body between an item header and the
  next item marker (TOC stubs lose). Verified on Apple's live 10-K: 68K-char Risk
  Factors + 18K-char MD&A extracted cleanly.
- **Citations are first-class** — every chunk's metadata carries ticker, form,
  accession number, filing date, section and SEC URL; retrieval returns these as
  a `Citation`, and answers must cite inline `[n]`.
- **Idempotent ingestion** — chunk IDs are `uuid5(accession+section+index)`, so
  re-ingesting upserts instead of duplicating.
- **Optional & graceful** — `ENABLE_RAG=false` by default; the Research Agent
  pulls filing context only when enabled, and a missing/empty store never breaks
  a run. Qdrant backend is in-memory (dev), on-disk (`QDRANT_PATH`) or server/cloud
  (`QDRANT_URL`).

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
│   ├── rag/                    # ── RAG over SEC filings ──
│   │   ├── filings.py          # download 10-K/10-Q from EDGAR
│   │   ├── parser.py           # extract Risk Factors (1A) + MD&A
│   │   ├── chunking.py         # citation-rich LangChain chunks
│   │   ├── embeddings.py       # OpenAI embeddings
│   │   ├── vectorstore.py      # Qdrant store wiring
│   │   ├── ingest.py           # download→…→store pipeline (+ CLI)
│   │   ├── retriever.py        # retrieval + cited answers
│   │   └── schemas.py          # FilingRef / Citation / RAGAnswer
│   └── tools/
│       ├── financials.py       # tool wrappers over FinancialDataService
│       ├── research_rag.py     # tool wrapper over the RAG retriever
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

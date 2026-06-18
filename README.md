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

## ⚖️ Multi-agent debate (Bull vs Bear, judged)

`alphamind/debate/` pits two adversarial agents against each other over multiple
rounds and has a Judge rule on the outcome — surfacing the strongest case on both
sides instead of a single blended view.

```
START → bull → bear ──(more rounds?)──► bull        (loop over N rounds)
                     └──(done)────────► bull_closing → bear_closing → judge → END
```

- **Multi-round** — Bull and Bear alternate for `DEBATE_ROUNDS` rounds, each
  advancing new arguments and rebutting the opponent's latest points.
- **Shared memory** — the append-only `transcript` is read in full before every
  turn, so the debate genuinely builds round over round.
- **Structured reasoning** — each turn emits discrete `claims`, `rebuttals` and
  `evidence` (not prose); each closing thesis lists key points, the single
  strongest point, and honest weaknesses.
- **Confidence scores** — every argument, both closing theses, and the judge's
  verdict carry a calibrated 1-10 confidence.

```python
from alphamind.debate.graph import run_debate

result = run_debate("AAPL", rounds=2)
print(result.bull_thesis.thesis)          # Bull Thesis
print(result.bear_thesis.thesis)          # Bear Thesis
print(result.judge.winner, result.judge.recommendation, result.confidence)  # Judge Decision + Confidence
```

**API:** `POST /debate { "ticker": "AAPL", "rounds": 2 }` → `DebateResult`
(bull thesis, bear thesis, judge decision, confidence, full transcript). The
debate is grounded in the real multi-source financial briefing by default.

## 🧠 Persistent memory (PostgreSQL + LangGraph + vector)

`alphamind/memory/` gives AlphaMind long-term, cross-session memory so it builds
on prior work instead of starting cold every time.

| Memory | Stored as | Example |
|--------|-----------|---------|
| **User profile** | `am_users` | risk tolerance, sector preferences |
| **Company** | `am_companies` | what we concluded about a ticker |
| **Research history** | `am_research_history` | every past analysis, recallable |
| **Conversation** | `am_messages` (+ LangGraph checkpointer) | message log per thread |
| **Vector** | `am_memory_vectors` | embeddings for semantic recall |

**The headline capability — it remembers:**

```python
from alphamind.graph import analyze
from alphamind.schemas import AnalysisRequest

analyze(AnalysisRequest(ticker="NVDA", user_id="u1", thread_id="t1", remember=True))
# ...later, even in a new session...
analyze(AnalysisRequest(ticker="AMD", user_id="u1", thread_id="t1", remember=True))
# → the AMD run recalls the prior NVIDIA analysis and compares against it
```

**Hybrid retrieval strategy** (`memory/retrieval.py`) — a single similarity search
is brittle for terse follow-ups ("compare with AMD"), so recall blends three
signals and de-duplicates:
1. **Exact** — user profile + company memory for any explicit ticker.
2. **Semantic** — vector cosine similarity to the query.
3. **Recency** — the latest research, so the most recent analysis is always in
   context even when semantic similarity is weak.

**Storage** — PostgreSQL in production (`MEMORY_DB_URL`), local **SQLite** as a
zero-config dev fallback; the same SQLAlchemy code targets both. **LangGraph
memory** (`langgraph_memory.py`) adds a Postgres/in-memory **checkpointer** for
per-thread state and a long-term **store**. Memory is **off by default**
(`ENABLE_MEMORY=false`) and every hook degrades gracefully.

**API:** `POST /memory/profile`, `POST /memory/recall`, `GET /memory/history`,
`GET /memory/conversation/{thread_id}` — and `/analyze` accepts
`user_id` / `thread_id` / `remember`.

## 🔌 Model Context Protocol (MCP)

`alphamind/mcp/` connects the agents to external MCP servers and lets them
**discover and use tools dynamically** — nothing is hard-coded.

| Server | Package / source | Auth |
|--------|------------------|------|
| **Filesystem** | `@modelcontextprotocol/server-filesystem` | none |
| **GitHub** | `@modelcontextprotocol/server-github` | PAT (`GITHUB_TOKEN`) |
| **Browser** | `@modelcontextprotocol/server-puppeteer` | none |
| **Financial Data** | AlphaMind's own server over `FinancialDataService` | none |

**Components**
- **MCP manager** (`manager.py`) — connects to each enabled server and discovers
  its tools at runtime; per-server failures are isolated (recorded, not raised)
  so one broken server never takes down the rest.
- **Tool registry** (`registry.py`) — a live, namespaced (`github.create_issue`),
  searchable catalog of every discovered tool, plus a record of failed servers.
- **Authentication layer** (`auth.py`) — resolves each server's required
  credentials from env, validates them *before* spawning a process, and redacts
  secrets from all output.
- **Error handling** — typed `MCPError` hierarchy (`MCPAuthError`,
  `MCPConnectionError`, `MCPToolError`, `MCPToolNotFound`).

```python
from alphamind.mcp.manager import MCPManager

mgr = MCPManager(); mgr.connect_sync()
print(mgr.status())          # {connected, servers, tool_count, tools, failures}

from alphamind.mcp.agent import run_mcp_agent_sync
print(run_mcp_agent_sync("Get NVDA's revenue and EPS, then save a summary to notes.txt"))
```

The MCP agent (`agent.py`) is a LangGraph ReAct agent bound to *whatever* tools the
servers expose — it inspects the registry and decides which to call. **API:**
`GET /mcp/servers`, `POST /mcp/connect`, `POST /mcp/agent`. The reference servers
run via `npx` (Node.js required); the Financial server is pure-Python
(`python -m alphamind.mcp.servers.financial_server`). Off by default (`ENABLE_MCP`).

## 📊 LLM evaluation framework (LangSmith + Ragas)

`alphamind/eval/` scores agent outputs across five metrics, aggregates them into a
report with **failure analysis**, and ships a Streamlit **dashboard**.

| Metric | What it measures | How |
|--------|------------------|-----|
| **Faithfulness** | Are answer claims grounded in context? | claim-support core / Ragas |
| **Hallucination rate** | Fraction of unsupported claims (lower better) | claim-support core |
| **Retrieval quality** | Retrieved vs. gold-relevant contexts (F1) | overlap core / Ragas |
| **Tool-usage accuracy** | Tools used vs. expected (F1) | deterministic |
| **Response completeness** | Required points covered by the answer | coverage core |

Each metric has a **deterministic core** (no LLM needed → fully unit-tested), and
Ragas can swap in LLM-graded faithfulness/retrieval when references exist.

```bash
# Score pre-computed outputs offline, or run the live pipeline as the target:
python -m alphamind.eval.run --outputs outputs.json --out eval_report.json
python -m alphamind.eval.run --live --langsmith        # push results to LangSmith

streamlit run ui/eval_dashboard.py                      # dashboard
```

**Dashboard** shows: overall quality + per-metric **evaluation scores** (avg & pass
rate), **agent performance** (agent × metric breakdown), and **failure analysis**
(every failed metric with its reason, filterable, plus per-sample drill-down).

**LangSmith** (`langsmith_eval.py`) — push report runs/feedback and adapt the
metrics into `langsmith.evaluate` evaluators; enable tracing via
`LANGCHAIN_TRACING_V2`. **Ragas** (`ragas_eval.py`) — reference faithfulness/
retrieval scoring. Both lazy-imported and degrade gracefully.

## 💼 Portfolio Advisor agent

`alphamind/portfolio/` takes a **risk profile** + holdings and returns per-position
actions — **BUY / HOLD / REDUCE / AVOID** — with reasoning, after analyzing four
dimensions:

- **Diversification** — HHI, effective number of holdings, top-position concentration.
- **Sector exposure** — sector weights vs the profile's cap, overweight flags.
- **Portfolio risk** — weighted risk score + beta, risk level, alignment to tolerance.
- **Expected returns** — weighted (and risk-adjusted) return vs the target.

Risk tolerance (conservative / balanced / aggressive) sets the position/sector
caps and acceptable risk band. The action engine is **deterministic and
explainable** (overweight → REDUCE, sell-rated → AVOID/REDUCE, buy-rated + room →
BUY); an optional LLM adds the portfolio-level narrative.

```python
from alphamind.portfolio.advisor import advise
from alphamind.portfolio.schemas import PortfolioInput, RiskProfile, RiskTolerance, Holding

advice = advise(PortfolioInput(
    risk_profile=RiskProfile(risk_tolerance=RiskTolerance.BALANCED, target_return=0.08),
    holdings=[Holding(ticker="NVDA", weight=0.4, sector="Tech", recommendation="BUY", conviction=8, risk_score=6), ...],
), use_llm=False)

for p in advice.positions:
    print(p.ticker, p.action.value, "→", f"{p.target_weight:.0%}", "|", p.reasoning)
```

**API:** `POST /portfolio/advise` → `PortfolioAdvice` (the four analyses, per-position
actions, overall assessment, prioritized rebalancing actions).

## 🖥️ Frontend (Next.js terminal)

A professional **Bloomberg Terminal × OpenAI** research UI lives in `frontend/`
(Next.js 14 · TypeScript · Tailwind · shadcn-style · Recharts). Six pages —
Research Workspace, Company Analysis, Agent Reasoning Viewer, Financial Dashboard,
Portfolio Advisor, Evaluation Dashboard — displaying agent thoughts, debate
history, citations, financial charts, risk scores and confidence metrics.

```bash
cd frontend && npm install && npm run dev   # http://localhost:3000
```

Ships with mock data and a graceful API client, so it renders with **no backend**;
set `NEXT_PUBLIC_API_URL=http://localhost:8000` to go live. See `frontend/README.md`.

## 🚀 Production

AlphaMind ships production-ready: containers, CI/CD, and a hardened API.

| Concern | How |
|---------|-----|
| **Docker** | Multi-stage non-root `Dockerfile` (gunicorn + uvicorn), `frontend/Dockerfile`, `docker-compose.yml` (api + frontend + Postgres + Qdrant + Redis) |
| **CI/CD · GitHub Actions** | `ci.yml` (ruff + pytest + frontend build), `docker-publish.yml` (build & push images to GHCR/ECR), `codeql.yml` (SAST) |
| **Monitoring** | Prometheus `/metrics` (request count + latency histograms); `/health`, `/ready`, `/version` probes |
| **Logging** | Structured JSON logs (`LOG_JSON=true`) with a per-request `X-Request-ID` propagated into every log line |
| **Rate limiting** | Fixed-window limiter per API-key/IP (`RATE_LIMIT_*`); 429 + `Retry-After`; Redis-ready for multi-instance |
| **Authentication** | API-key auth (`X-API-Key` / `Bearer`), enabled via `AUTH_ENABLED` + `API_KEYS`; ops endpoints exempt |
| **API versioning** | Business endpoints under `/v1`; ops endpoints unversioned |
| **Tests** | Unit (rate limiter, auth, all agent/metric cores) + integration (TestClient: versioning, auth, rate limit, metrics) |

```bash
docker compose up --build        # full local stack
# or: gunicorn api.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

curl localhost:8000/health       # {"status":"ok"}
curl localhost:8000/version      # {"version":...,"api_version":"v1",...}
curl -X POST localhost:8000/v1/portfolio/advise -H 'X-API-Key: <key>' -d '{...}'
```

**AWS deployment architecture** (ECS Fargate · ALB · RDS · ElastiCache · Qdrant ·
ECR · Secrets Manager · CloudWatch · WAF) is documented in
[`docs/DEPLOYMENT_AWS.md`](docs/DEPLOYMENT_AWS.md).

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
│   ├── debate/                 # ── multi-agent Bull/Bear/Judge debate ──
│   │   ├── agents.py           # bull, bear, judge (+ closings)
│   │   ├── graph.py            # looped debate graph + run_debate()
│   │   ├── state.py            # shared-memory transcript state
│   │   ├── util.py             # round control + transcript rendering
│   │   └── schemas.py          # DebateArgument / SideThesis / JudgeDecision
│   ├── memory/                 # ── persistent memory (Postgres + vector) ──
│   │   ├── models.py           # SQLAlchemy tables (users/companies/research/msgs/vectors)
│   │   ├── db.py               # engine/DSN resolution (Postgres ↔ SQLite)
│   │   ├── vector.py           # embedding add/search (cosine)
│   │   ├── retrieval.py        # hybrid recall strategy (exact+recency+semantic)
│   │   ├── service.py          # MemoryService facade
│   │   ├── langgraph_memory.py # checkpointer + long-term store factories
│   │   └── schemas.py          # UserProfile / CompanyMemory / ResearchRecord / …
│   ├── mcp/                    # ── Model Context Protocol integration ──
│   │   ├── specs.py            # filesystem / github / browser / financial servers
│   │   ├── auth.py             # credential resolution + validation
│   │   ├── manager.py          # MCPManager: connect + dynamic tool discovery
│   │   ├── registry.py         # ToolRegistry: namespaced, searchable catalog
│   │   ├── agent.py            # ReAct agent over discovered tools
│   │   ├── schemas.py          # MCPServerSpec / ToolInfo
│   │   └── servers/financial_server.py  # local Financial Data MCP server
│   ├── eval/                   # ── LLM evaluation framework ──
│   │   ├── metrics.py          # 5 metrics (deterministic cores)
│   │   ├── report.py           # aggregation + failure analysis
│   │   ├── runner.py           # EvaluationRunner
│   │   ├── ragas_eval.py       # Ragas integration
│   │   ├── langsmith_eval.py   # LangSmith datasets/feedback/evaluators
│   │   ├── datasets.py         # golden set + loader
│   │   ├── run.py              # CLI → report JSON
│   │   └── schemas.py          # EvalSample / AgentOutput / EvalReport
│   ├── portfolio/              # ── Portfolio Advisor agent ──
│   │   ├── analytics.py        # diversification/sector/risk/return + rec engine
│   │   ├── agent.py            # optional LLM narrative
│   │   ├── advisor.py          # orchestrator → PortfolioAdvice
│   │   └── schemas.py          # RiskProfile / Holding / PortfolioAdvice
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

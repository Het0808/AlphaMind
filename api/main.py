"""AlphaMind FastAPI service — production entrypoint.

Ops endpoints (unversioned): /health, /ready, /version, /metrics.
Business endpoints are served under the versioned prefix /v1 and protected by the
auth + rate-limit middleware stack. Heavy dependencies are imported lazily inside
handlers so the app imports cleanly for testing and fast cold starts.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from alphamind import __version__
from alphamind.config import get_settings
from alphamind.observability.logging import configure_logging
from alphamind.observability.metrics import render_metrics
from alphamind.portfolio.schemas import PortfolioInput
from alphamind.resolver import TickerResolutionError, resolve_ticker
from alphamind.schemas import AnalysisRequest, InvestmentReport
from .middleware import RateLimitMiddleware, RequestContextMiddleware
from .security import require_api_key

settings = get_settings()
configure_logging(json_logs=settings.log_json, level=settings.log_level)
logger = logging.getLogger("alphamind.api")

API_VERSION = "v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AlphaMind API starting (env=%s, sha=%s)", settings.environment, settings.git_sha)
    yield
    logger.info("AlphaMind API shutting down")


app = FastAPI(
    title="AlphaMind",
    description="Agentic AI Investment Research Platform",
    version=__version__,
    lifespan=lifespan,
)

# Middleware (outermost first): context/logging/metrics, then rate limiting, then CORS.
app.add_middleware(RequestContextMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────────────────────
# Operational endpoints (unversioned, unauthenticated, not rate-limited)
# ──────────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["ops"])
def health() -> dict:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/ready", tags=["ops"])
def ready() -> dict:
    """Readiness probe — reports dependency configuration."""
    s = get_settings()
    checks = {"openai_configured": s.is_configured, "auth_enabled": s.auth_enabled}
    return {"status": "ready" if all([True]) else "degraded", "checks": checks}


@app.get("/version", tags=["ops"])
def version() -> dict:
    s = get_settings()
    return {"version": __version__, "api_version": API_VERSION, "environment": s.environment, "git_sha": s.git_sha}


@app.get("/metrics", tags=["ops"])
def metrics() -> Response:
    if not get_settings().metrics_enabled:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    body, content_type = render_metrics()
    return Response(content=body, media_type=content_type)


# ──────────────────────────────────────────────────────────────────────────
# Versioned business API (/v1) — auth-protected
# ──────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix=f"/{API_VERSION}", dependencies=[Depends(require_api_key)])


def _require_openai() -> None:
    if not get_settings().is_configured:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured.")


class ResolveRequest(BaseModel):
    query: str


@router.post("/resolve", tags=["research"])
def resolve_endpoint(req: ResolveRequest) -> dict:
    """Resolve a company name or symbol (US/India) to a canonical ticker."""
    try:
        return resolve_ticker(req.query).model_dump()
    except TickerResolutionError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc), "query": exc.query,
                    "suggestions": [s.model_dump() for s in exc.suggestions]},
        ) from exc


@router.post("/analyze", response_model=InvestmentReport, tags=["research"])
def analyze_endpoint(request: AnalysisRequest) -> InvestmentReport:
    _require_openai()
    try:
        from alphamind.graph import analyze  # lazy: pulls langgraph only when used

        logger.info("Analyzing %s", request.ticker)
        return analyze(request)
    except TickerResolutionError as exc:
        raise HTTPException(
            status_code=400,
            detail={"message": str(exc), "query": exc.query,
                    "suggestions": [s.model_dump() for s in exc.suggestions]},
        ) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("Analysis failed for %s", request.ticker)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


# ── RAG over SEC filings ──
class IngestRequest(BaseModel):
    ticker: str
    forms: List[str] = Field(default_factory=lambda: ["10-K", "10-Q"])
    limit: int = 2


class FilingQuery(BaseModel):
    ticker: str
    query: str
    k: Optional[int] = None


@router.post("/filings/ingest", tags=["rag"])
def filings_ingest(req: IngestRequest) -> dict:
    try:
        from alphamind.rag.ingest import FilingIngestor

        return FilingIngestor().ingest_ticker(req.ticker, forms=req.forms, limit=req.limit).model_dump()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingestion failed for %s", req.ticker)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc


@router.post("/filings/search", tags=["rag"])
def filings_search(req: FilingQuery) -> dict:
    from alphamind.tools import search_filings

    return search_filings(req.ticker, req.query, k=req.k)


@router.post("/filings/qa", tags=["rag"])
def filings_qa(req: FilingQuery) -> dict:
    _require_openai()
    try:
        from alphamind.rag.retriever import FilingRetriever

        return FilingRetriever().answer(req.query, ticker=req.ticker, k=req.k).model_dump()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Filings QA failed for %s", req.ticker)
        raise HTTPException(status_code=500, detail=f"Filings QA failed: {exc}") from exc


# ── Debate ──
class DebateRequest(BaseModel):
    ticker: str
    rounds: Optional[int] = None


@router.post("/debate", tags=["debate"])
def debate_endpoint(req: DebateRequest) -> dict:
    _require_openai()
    try:
        from alphamind.debate.graph import run_debate

        return run_debate(req.ticker, rounds=req.rounds).model_dump()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Debate failed for %s", req.ticker)
        raise HTTPException(status_code=500, detail=f"Debate failed: {exc}") from exc


# ── Memory ──
class ProfileRequest(BaseModel):
    user_id: str
    name: Optional[str] = None
    risk_tolerance: Optional[str] = None
    preferences: dict = Field(default_factory=dict)


class RecallRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    ticker: Optional[str] = None


def _memory_service():
    from alphamind.memory.service import get_memory_service

    return get_memory_service()


@router.post("/memory/profile", tags=["memory"])
def memory_profile(req: ProfileRequest) -> dict:
    try:
        return _memory_service().upsert_user_profile(
            req.user_id, name=req.name, risk_tolerance=req.risk_tolerance, preferences=req.preferences
        ).model_dump()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Memory error: {exc}") from exc


@router.post("/memory/recall", tags=["memory"])
def memory_recall(req: RecallRequest) -> dict:
    try:
        ctx = _memory_service().recall(req.query, user_id=req.user_id, ticker=req.ticker)
        return {"context": ctx.format(), "has_content": ctx.has_content(), **ctx.model_dump()}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Memory error: {exc}") from exc


@router.get("/memory/history", tags=["memory"])
def memory_history(user_id: Optional[str] = None, ticker: Optional[str] = None, limit: int = 10) -> dict:
    try:
        records = _memory_service().get_research_history(user_id=user_id, ticker=ticker, limit=limit)
        return {"records": [r.model_dump() for r in records]}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Memory error: {exc}") from exc


@router.get("/memory/conversation/{thread_id}", tags=["memory"])
def memory_conversation(thread_id: str, limit: int = 50) -> dict:
    try:
        messages = _memory_service().get_conversation(thread_id, limit=limit)
        return {"messages": [m.model_dump() for m in messages]}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Memory error: {exc}") from exc


# ── MCP ──
class MCPAgentRequest(BaseModel):
    query: str


@router.get("/mcp/servers", tags=["mcp"])
def mcp_servers() -> dict:
    from alphamind.mcp.specs import default_server_specs

    return {"servers": [s.redacted() for s in default_server_specs()]}


@router.post("/mcp/connect", tags=["mcp"])
def mcp_connect() -> dict:
    try:
        from alphamind.mcp.manager import MCPManager

        manager = MCPManager()
        manager.connect_sync()
        return manager.status()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"MCP connect failed: {exc}") from exc


@router.post("/mcp/agent", tags=["mcp"])
def mcp_agent(req: MCPAgentRequest) -> dict:
    _require_openai()
    try:
        from alphamind.mcp.agent import run_mcp_agent_sync

        return {"query": req.query, "answer": run_mcp_agent_sync(req.query)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"MCP agent failed: {exc}") from exc


# ── Portfolio Advisor ──
@router.post("/portfolio/advise", tags=["portfolio"])
def portfolio_advise(req: PortfolioInput, use_llm: bool = True) -> dict:
    try:
        from alphamind.portfolio.advisor import advise

        return advise(req, use_llm=use_llm and get_settings().is_configured).model_dump()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Portfolio advice failed")
        raise HTTPException(status_code=500, detail=f"Portfolio advice failed: {exc}") from exc


app.include_router(router)


def run() -> None:
    """`python -m api.main` entrypoint to launch the server."""
    import uvicorn

    s = get_settings()
    uvicorn.run("api.main:app", host=s.api_host, port=s.api_port, reload=False)


if __name__ == "__main__":
    run()

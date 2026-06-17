"""FastAPI service exposing the AlphaMind agent graph.

Endpoints:
    GET  /health           — liveness + configuration check
    POST /analyze          — run the full multi-agent pipeline, return InvestmentReport
    POST /filings/ingest   — download & index SEC filings into Qdrant (RAG)
    POST /filings/search   — semantic search over filings, returns cited chunks
    POST /filings/qa       — RAG answer over filings with exact citations
    POST /debate           — multi-round Bull/Bear/Judge debate with confidence
"""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from alphamind.config import get_settings
from alphamind.graph import analyze
from alphamind.schemas import AnalysisRequest, InvestmentReport

logging.basicConfig(level=get_settings().log_level)
logger = logging.getLogger("alphamind.api")

app = FastAPI(
    title="AlphaMind",
    description="Agentic AI Investment Research Platform",
    version="0.1.0",
)

# CORS — tighten `allow_origins` to your UI domain(s) in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "model": settings.openai_model,
        "openai_configured": settings.is_configured,
    }


@app.post("/analyze", response_model=InvestmentReport)
def analyze_endpoint(request: AnalysisRequest) -> InvestmentReport:
    settings = get_settings()
    if not settings.is_configured:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured.")

    try:
        logger.info("Analyzing %s", request.ticker)
        return analyze(request)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Analysis failed for %s", request.ticker)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


# ──────────────────────────────────────────────────────────────────────────
# RAG over SEC filings
# ──────────────────────────────────────────────────────────────────────────
class IngestRequest(BaseModel):
    ticker: str
    forms: List[str] = Field(default_factory=lambda: ["10-K", "10-Q"])
    limit: int = 2


class FilingSearchRequest(BaseModel):
    ticker: str
    query: str
    k: Optional[int] = None


class FilingQARequest(BaseModel):
    ticker: str
    query: str
    k: Optional[int] = None


@app.post("/filings/ingest")
def filings_ingest(req: IngestRequest) -> dict:
    """Download, parse, chunk, embed and index a company's filings into Qdrant."""
    try:
        from alphamind.rag.ingest import FilingIngestor

        result = FilingIngestor().ingest_ticker(req.ticker, forms=req.forms, limit=req.limit)
        return result.model_dump()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Ingestion failed for %s", req.ticker)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc


@app.post("/filings/search")
def filings_search(req: FilingSearchRequest) -> dict:
    """Semantic search over indexed filings; each hit carries an exact citation."""
    from alphamind.tools import search_filings

    return search_filings(req.ticker, req.query, k=req.k)


@app.post("/filings/qa")
def filings_qa(req: FilingQARequest) -> dict:
    """Answer a question grounded in filings, returning inline [n] citations."""
    settings = get_settings()
    if not settings.is_configured:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured.")
    try:
        from alphamind.rag.retriever import FilingRetriever

        return FilingRetriever().answer(req.query, ticker=req.ticker, k=req.k).model_dump()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Filings QA failed for %s", req.ticker)
        raise HTTPException(status_code=500, detail=f"Filings QA failed: {exc}") from exc


# ──────────────────────────────────────────────────────────────────────────
# Multi-agent debate
# ──────────────────────────────────────────────────────────────────────────
class DebateRequest(BaseModel):
    ticker: str
    rounds: Optional[int] = None


@app.post("/debate")
def debate_endpoint(req: DebateRequest) -> dict:
    """Run a Bull/Bear/Judge debate and return theses, verdict and confidence."""
    settings = get_settings()
    if not settings.is_configured:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured.")
    try:
        from alphamind.debate.graph import run_debate

        return run_debate(req.ticker, rounds=req.rounds).model_dump()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Debate failed for %s", req.ticker)
        raise HTTPException(status_code=500, detail=f"Debate failed: {exc}") from exc


def run() -> None:
    """`python -m api.main` / console entrypoint to launch the server."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()

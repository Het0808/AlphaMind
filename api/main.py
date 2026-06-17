"""FastAPI service exposing the AlphaMind agent graph.

Endpoints:
    GET  /health    — liveness + configuration check
    POST /analyze   — run the full multi-agent pipeline, return InvestmentReport
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

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

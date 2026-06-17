"""Agent-facing wrapper over the RAG retriever.

Returns plain dicts with the retrieved text plus the *exact* filing reference and
URL for each hit. Heavy RAG dependencies are imported lazily and all errors are
swallowed into an `error` field, so a missing/empty vector store never breaks a
graph run — the agent simply proceeds without filing context.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def search_filings(ticker: str, query: str, *, k: Optional[int] = None) -> Dict[str, Any]:
    """Retrieve relevant SEC filing passages for a ticker, with citations."""
    try:
        from ..rag.retriever import FilingRetriever

        chunks = FilingRetriever().retrieve(query, ticker=ticker, k=k)
        return {
            "ticker": ticker.upper(),
            "results": [
                {
                    "text": c.text,
                    "reference": c.citation.reference(),
                    "url": c.citation.url,
                    "section": c.citation.section,
                    "form": c.citation.form,
                    "filing_date": c.citation.filing_date,
                    "accession": c.citation.accession,
                    "score": c.score,
                }
                for c in chunks
            ],
        }
    except Exception as exc:  # noqa: BLE001 - RAG is optional; degrade gracefully
        logger.warning("search_filings(%s) failed: %s", ticker, exc)
        return {"ticker": ticker.upper(), "error": str(exc), "results": []}

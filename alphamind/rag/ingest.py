"""Ingestion pipeline: download → parse → extract → chunk → embed → store.

Run as a module:  python -m alphamind.rag.ingest AAPL MSFT --forms 10-K 10-Q --limit 2

Chunk IDs are deterministic (uuid5 of accession+section+chunk_index), so
re-ingesting a filing upserts in place instead of creating duplicates.
"""

from __future__ import annotations

import logging
import uuid
from typing import List, Sequence

from pydantic import BaseModel

from .chunking import chunk_sections
from .filings import SECFilingsClient
from .parser import extract_sections
from .schemas import FilingRef
from .vectorstore import get_vectorstore

logger = logging.getLogger(__name__)

_NAMESPACE = uuid.UUID("a1f3c0de-0000-4000-8000-000000000000")


class IngestResult(BaseModel):
    ticker: str
    filings_processed: int
    sections_extracted: int
    chunks_indexed: int
    filings: List[FilingRef] = []
    warnings: List[str] = []


def _chunk_id(metadata: dict) -> str:
    key = f"{metadata['accession']}:{metadata['section']}:{metadata['chunk_index']}"
    return str(uuid.uuid5(_NAMESPACE, key))


class FilingIngestor:
    def __init__(self, client: SECFilingsClient | None = None):
        self._client = client or SECFilingsClient()

    def ingest_ticker(
        self,
        ticker: str,
        forms: Sequence[str] = ("10-K", "10-Q"),
        limit: int = 2,
    ) -> IngestResult:
        ticker = ticker.upper()
        warnings: List[str] = []

        refs = self._client.list_filings(ticker, forms=forms, limit=limit)
        triples = []
        for ref in refs:
            try:
                html = self._client.fetch_document(ref)
                _, sections = extract_sections(html, ref.form)
            except Exception as exc:  # noqa: BLE001 - skip a bad filing, keep going
                logger.warning("Failed to process %s %s: %s", ticker, ref.accession, exc)
                warnings.append(f"{ref.form} {ref.accession}: {exc}")
                continue
            if not sections:
                warnings.append(f"{ref.form} {ref.accession}: no target sections found")
            for name, text in sections.items():
                triples.append((ref, name, text))

        docs = chunk_sections(triples)
        if docs:
            ids = [_chunk_id(d.metadata) for d in docs]
            get_vectorstore().add_documents(docs, ids=ids)

        return IngestResult(
            ticker=ticker,
            filings_processed=len(refs),
            sections_extracted=len(triples),
            chunks_indexed=len(docs),
            filings=refs,
            warnings=warnings,
        )


def _main(argv: List[str] | None = None) -> None:
    import argparse

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="Ingest SEC filings into Qdrant.")
    parser.add_argument("tickers", nargs="+", help="Ticker symbols, e.g. AAPL MSFT")
    parser.add_argument("--forms", nargs="+", default=["10-K", "10-Q"])
    parser.add_argument("--limit", type=int, default=2, help="Filings per form-set per ticker")
    args = parser.parse_args(argv)

    ingestor = FilingIngestor()
    for ticker in args.tickers:
        result = ingestor.ingest_ticker(ticker, forms=args.forms, limit=args.limit)
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    _main()

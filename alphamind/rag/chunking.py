"""Chunk extracted filing sections into embedding-ready LangChain Documents.

Each chunk carries the full filing provenance in its metadata (ticker, form,
accession, filing date, section, URL, chunk index) — this metadata is exactly
what powers citations at retrieval time.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..config import get_settings
from .schemas import FilingRef


def chunk_sections(
    sections: List[Tuple[FilingRef, str, str]],
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> List[Document]:
    """Split (filing, section_name, section_text) triples into Documents.

    Returns LangChain `Document`s with citation-ready metadata.
    """
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size or settings.rag_chunk_size,
        chunk_overlap=chunk_overlap or settings.rag_chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    docs: List[Document] = []
    for filing, section_name, section_text in sections:
        for idx, chunk in enumerate(splitter.split_text(section_text)):
            metadata: Dict[str, object] = {
                "ticker": filing.ticker,
                "cik": filing.cik,
                "form": filing.form,
                "accession": filing.accession,
                "filing_date": filing.filing_date,
                "period_of_report": filing.period_of_report,
                "section": section_name,
                "source_url": filing.url,
                "chunk_index": idx,
            }
            docs.append(Document(page_content=chunk, metadata=metadata))
    return docs

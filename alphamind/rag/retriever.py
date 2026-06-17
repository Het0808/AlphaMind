"""Retrieval pipeline with exact filing citations.

`retrieve` does filtered similarity search over Qdrant and converts each hit into
a `RetrievedChunk` whose `Citation` carries the precise filing reference. `answer`
builds a numbered context and asks the LLM to cite sources inline as [n], then
returns the answer alongside the structured citations.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from qdrant_client import models as qmodels

from ..config import get_settings
from ..llm import get_llm
from .schemas import Citation, RAGAnswer, RetrievedChunk
from .vectorstore import get_vectorstore

logger = logging.getLogger(__name__)

_ANSWER_SYSTEM = (
    "You are AlphaMind's filings analyst. Answer the question using ONLY the "
    "numbered SEC filing excerpts provided. Cite every claim inline with the "
    "bracketed source number, e.g. [1], [2]. If the excerpts do not contain the "
    "answer, say so explicitly. Never fabricate figures or citations."
)


class FilingRetriever:
    def __init__(self, vectorstore=None):
        self._vs = vectorstore  # lazily resolved so importing this module is cheap

    @property
    def vs(self):
        if self._vs is None:
            self._vs = get_vectorstore()
        return self._vs

    @staticmethod
    def _build_filter(ticker: Optional[str], form: Optional[str]) -> Optional[qmodels.Filter]:
        conditions = []
        if ticker:
            conditions.append(
                qmodels.FieldCondition(key="metadata.ticker", match=qmodels.MatchValue(value=ticker.upper()))
            )
        if form:
            conditions.append(
                qmodels.FieldCondition(key="metadata.form", match=qmodels.MatchValue(value=form))
            )
        return qmodels.Filter(must=conditions) if conditions else None

    def retrieve(
        self,
        query: str,
        *,
        ticker: Optional[str] = None,
        form: Optional[str] = None,
        k: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        k = k or get_settings().rag_top_k
        results = self.vs.similarity_search_with_score(
            query, k=k, filter=self._build_filter(ticker, form)
        )
        chunks: List[RetrievedChunk] = []
        for doc, score in results:
            md = doc.metadata or {}
            citation = Citation(
                ticker=md.get("ticker", ticker or "?"),
                form=md.get("form", "?"),
                section=md.get("section", "?"),
                accession=md.get("accession", "?"),
                filing_date=md.get("filing_date", "?"),
                url=md.get("source_url", ""),
                snippet=doc.page_content[:240].strip(),
                score=float(score),
            )
            chunks.append(RetrievedChunk(text=doc.page_content, score=float(score), citation=citation))
        return chunks

    def answer(self, query: str, *, ticker: Optional[str] = None, k: Optional[int] = None) -> RAGAnswer:
        chunks = self.retrieve(query, ticker=ticker, k=k)
        if not chunks:
            return RAGAnswer(query=query, answer="No relevant filing excerpts were found.", citations=[])

        context = "\n\n".join(
            f"[{i + 1}] ({c.citation.reference()} — {c.citation.url})\n{c.text}"
            for i, c in enumerate(chunks)
        )
        response = get_llm(temperature=0.0).invoke(
            [
                SystemMessage(content=_ANSWER_SYSTEM),
                HumanMessage(content=f"Question: {query}\n\nSEC filing excerpts:\n{context}\n\nAnswer with inline [n] citations."),
            ]
        )
        return RAGAnswer(query=query, answer=response.content, citations=[c.citation for c in chunks])

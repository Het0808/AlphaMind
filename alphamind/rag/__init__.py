"""AlphaMind RAG layer — retrieval-augmented generation over SEC filings.

Pipeline: download (EDGAR) → parse 10-K/10-Q → extract Risk Factors & MD&A →
chunk → embed (OpenAI) → store (Qdrant) → retrieve with exact filing citations.

Only `schemas` is imported eagerly here so `import alphamind.rag` stays light;
the heavy components (embeddings/Qdrant/LangChain) are imported from their
submodules on demand.
"""

from .schemas import Citation, FilingRef, RAGAnswer, RetrievedChunk

__all__ = ["FilingRef", "Citation", "RetrievedChunk", "RAGAnswer"]

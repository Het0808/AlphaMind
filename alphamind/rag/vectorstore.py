"""Qdrant vector store wiring.

Supports three backends, chosen by config:
  • QDRANT_URL   → a Qdrant server / Qdrant Cloud (with optional API key)
  • QDRANT_PATH  → an on-disk local store
  • (neither)    → an ephemeral in-memory store (great for dev/CI)

The client is a process-wide singleton so the in-memory/on-disk store is shared
between ingestion and retrieval within the same process.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client import models as qmodels

from ..config import get_settings
from .embeddings import get_embeddings

logger = logging.getLogger(__name__)


@lru_cache
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    if settings.qdrant_url:
        logger.info("Qdrant: connecting to %s", settings.qdrant_url)
        return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
    if settings.qdrant_path:
        logger.info("Qdrant: on-disk store at %s", settings.qdrant_path)
        return QdrantClient(path=settings.qdrant_path)
    logger.info("Qdrant: ephemeral in-memory store")
    return QdrantClient(location=":memory:")


def ensure_collection(client: QdrantClient, name: str, embeddings) -> None:
    """Create the collection (sized to the embedding dimension) if it doesn't exist."""
    existing = {c.name for c in client.get_collections().collections}
    if name in existing:
        return
    dim = len(embeddings.embed_query("dimension probe"))
    client.create_collection(
        collection_name=name,
        vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
    )
    logger.info("Qdrant: created collection '%s' (dim=%d)", name, dim)


@lru_cache
def get_vectorstore() -> QdrantVectorStore:
    settings = get_settings()
    embeddings = get_embeddings()
    client = get_qdrant_client()
    ensure_collection(client, settings.qdrant_collection, embeddings)
    return QdrantVectorStore(
        client=client,
        collection_name=settings.qdrant_collection,
        embedding=embeddings,
    )

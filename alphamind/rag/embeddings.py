"""OpenAI embeddings factory for the RAG layer."""

from __future__ import annotations

from functools import lru_cache

from langchain_openai import OpenAIEmbeddings

from ..config import get_settings


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    settings = get_settings()
    return OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)

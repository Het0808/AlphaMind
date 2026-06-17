"""Centralized, validated configuration loaded from environment / .env.

Using pydantic-settings means every setting is type-checked at startup and
there is a single source of truth for configuration across the API, the graph
and the Streamlit UI.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_temperature: float = 0.1
    request_timeout: int = 60

    # ── Financial data providers ──
    fmp_api_key: str = ""
    sec_user_agent: str = "AlphaMind/0.1 (contact: set-your-email@example.com)"
    enable_yahoo: bool = True
    enable_edgar: bool = True
    enable_fmp: bool = True
    data_cache_ttl: int = 3600  # seconds to cache a financial snapshot

    # ── RAG over SEC filings ──
    enable_rag: bool = False  # off by default so the graph runs without a vector store
    embedding_model: str = "text-embedding-3-small"
    qdrant_url: str = ""          # e.g. http://localhost:6333 or a Qdrant Cloud URL
    qdrant_api_key: str = ""      # for Qdrant Cloud
    qdrant_path: str = ""         # on-disk local store, e.g. ./qdrant_data
    qdrant_collection: str = "alphamind_filings"
    rag_chunk_size: int = 1200
    rag_chunk_overlap: int = 150
    rag_top_k: int = 5

    # API server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Streamlit -> API
    alphamind_api_url: str = "http://localhost:8000"

    # Observability
    log_level: str = "INFO"

    @property
    def is_configured(self) -> bool:
        """True when we have a usable OpenAI key."""
        return bool(self.openai_api_key) and self.openai_api_key != "sk-your-key-here"


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so settings are parsed exactly once per process."""
    return Settings()

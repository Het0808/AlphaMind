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

    # ── Multi-agent debate ──
    debate_rounds: int = 2  # number of Bull/Bear exchange rounds before judging

    # ── Persistent memory ──
    enable_memory: bool = False
    memory_db_url: str = ""  # SQLAlchemy DSN, e.g. postgresql+psycopg://u:p@host:5432/db
    memory_sqlite_path: str = "alphamind_memory.db"  # used when memory_db_url is blank
    memory_recall_k: int = 5

    # ── Model Context Protocol (MCP) ──
    enable_mcp: bool = False
    npx_command: str = "npx"  # launcher for the Node-based reference MCP servers
    mcp_filesystem_root: str = "./workspace"
    mcp_browser_package: str = "@modelcontextprotocol/server-puppeteer"
    github_token: str = ""  # GitHub PAT for the GitHub MCP server
    mcp_enable_filesystem: bool = True
    mcp_enable_github: bool = True
    mcp_enable_browser: bool = True
    mcp_enable_financial: bool = True

    # ── LLM evaluation ──
    eval_threshold: float = 0.7  # default pass threshold for metrics
    eval_report_path: str = "eval_report.json"
    langsmith_api_key: str = ""
    langsmith_project: str = "alphamind"
    langchain_tracing_v2: bool = False

    # ── Production / serving ──
    environment: str = "development"     # development | staging | production
    git_sha: str = "dev"                  # injected at build time
    log_json: bool = False                # structured JSON logs (enable in prod)
    cors_origins: str = "*"               # comma-separated allowed origins
    # Authentication (API keys)
    auth_enabled: bool = False
    api_keys: str = ""                    # comma-separated accepted API keys
    # Rate limiting (fixed-window per client)
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 60         # requests per window
    rate_limit_window: int = 60           # window in seconds
    redis_url: str = ""                   # optional, for distributed rate limiting
    # Observability
    metrics_enabled: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()] or ["*"]

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

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

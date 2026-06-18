"""Authentication: API-key auth as a FastAPI dependency.

Accepts a key via `X-API-Key` or `Authorization: Bearer <key>`. When
`AUTH_ENABLED=false` (default for local/dev) the dependency is a no-op so the API
stays open; in production set `AUTH_ENABLED=true` and `API_KEYS=key1,key2`.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, status

from alphamind.config import get_settings


def extract_key(x_api_key: str | None, authorization: str | None) -> str | None:
    if x_api_key:
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None),
) -> str:
    """Dependency that enforces a valid API key when auth is enabled."""
    settings = get_settings()
    if not settings.auth_enabled:
        return "anonymous"

    key = extract_key(x_api_key, authorization)
    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key (X-API-Key or Authorization: Bearer).",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if key not in settings.api_key_set:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key.")
    return key

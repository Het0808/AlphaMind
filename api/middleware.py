"""Production middleware: request context + access logs, metrics, rate limiting."""

from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from alphamind.config import get_settings
from alphamind.observability.logging import set_request_id
from alphamind.observability.metrics import observe_request
from .ratelimit import RateLimiter

logger = logging.getLogger("alphamind.access")

# Paths exempt from auth/rate-limiting (ops endpoints).
EXEMPT_PATHS = {"/health", "/ready", "/version", "/metrics", "/docs", "/openapi.json", "/redoc"}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, times the request, logs access, records metrics."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        set_request_id(request_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration = time.perf_counter() - start
            logger.exception("unhandled error %s %s", request.method, request.url.path)
            observe_request(request.method, request.url.path, 500, duration)
            return JSONResponse(status_code=500, content={"detail": "Internal server error", "request_id": request_id})

        duration = time.perf_counter() - start
        response.headers["X-Request-ID"] = request_id
        observe_request(request.method, request.url.path, response.status_code, duration)
        logger.info(
            "%s %s -> %d (%.1fms)", request.method, request.url.path, response.status_code, duration * 1000,
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window rate limiting keyed by API key or client IP."""

    def __init__(self, app):
        super().__init__(app)
        s = get_settings()
        self.enabled = s.rate_limit_enabled
        self.limiter = RateLimiter(s.rate_limit_requests, s.rate_limit_window)

    def _client_key(self, request: Request) -> str:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key}"
        client = request.client.host if request.client else "unknown"
        return f"ip:{client}"

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled or request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        decision = self.limiter.check(self._client_key(request))
        if not decision.allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(decision.reset_in), "X-RateLimit-Remaining": "0"},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        response.headers["X-RateLimit-Limit"] = str(self.limiter.limit)
        return response

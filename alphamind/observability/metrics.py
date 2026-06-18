"""Prometheus metrics with a graceful no-op fallback.

If `prometheus_client` isn't installed, the functions become no-ops and the
/metrics endpoint reports that metrics are disabled — the app still runs.
"""

from __future__ import annotations

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

    _ENABLED = True
    _REQUESTS = Counter(
        "alphamind_http_requests_total", "HTTP requests", ["method", "path", "status"],
    )
    _LATENCY = Histogram(
        "alphamind_http_request_duration_seconds", "Request latency", ["method", "path"],
    )
except Exception:  # noqa: BLE001 - prometheus optional
    _ENABLED = False
    CONTENT_TYPE_LATEST = "text/plain"


def observe_request(method: str, path: str, status: int, duration: float) -> None:
    if not _ENABLED:
        return
    _REQUESTS.labels(method=method, path=path, status=str(status)).inc()
    _LATENCY.labels(method=method, path=path).observe(duration)


def render_metrics() -> tuple[bytes, str]:
    if not _ENABLED:
        return b"# prometheus_client not installed\n", "text/plain"
    return generate_latest(), CONTENT_TYPE_LATEST

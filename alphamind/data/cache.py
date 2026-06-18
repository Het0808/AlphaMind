"""A small, dependency-free, thread-safe TTL cache.

Financial fundamentals change at most quarterly and market data within seconds is
irrelevant to research, so caching by ticker for a configurable TTL massively
cuts latency, cost and the risk of hitting provider rate limits.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional, Tuple


class TTLCache:
    """In-memory cache with per-entry expiry and simple size-bounded eviction."""

    def __init__(self, ttl_seconds: int = 3600, maxsize: int = 512):
        self._ttl = ttl_seconds
        self._maxsize = maxsize
        self._store: Dict[str, Tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.monotonic() > expires_at:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, *, ttl: Optional[int] = None) -> None:
        with self._lock:
            if key not in self._store and len(self._store) >= self._maxsize:
                # Evict the entry closest to expiry to bound memory.
                oldest = min(self._store, key=lambda k: self._store[k][0])
                self._store.pop(oldest, None)
            self._store[key] = (time.monotonic() + (ttl or self._ttl), value)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._store)

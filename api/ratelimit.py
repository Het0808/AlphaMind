"""Fixed-window rate limiter — pure and unit-testable.

In-memory and thread-safe; for multi-instance deployments back it with Redis
(swap `_buckets` for an atomic INCR+EXPIRE). Keyed by API key or client IP.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class Decision:
    allowed: bool
    remaining: int
    reset_in: int  # seconds until the window resets


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._buckets: Dict[str, Tuple[float, int]] = {}  # key -> (window_start, count)
        self._lock = threading.Lock()

    def check(self, key: str, *, now: Optional[float] = None) -> Decision:
        now = time.monotonic() if now is None else now
        with self._lock:
            start, count = self._buckets.get(key, (now, 0))
            if now - start >= self.window:
                start, count = now, 0  # window expired → reset

            reset_in = max(0, int(self.window - (now - start)))
            if count >= self.limit:
                self._buckets[key] = (start, count)
                return Decision(allowed=False, remaining=0, reset_in=reset_in)

            count += 1
            self._buckets[key] = (start, count)
            return Decision(allowed=True, remaining=self.limit - count, reset_in=reset_in)

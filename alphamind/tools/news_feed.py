"""News feed tool.

Pulls recent headlines from yfinance. Swap `get_recent_news` for a dedicated
provider (NewsAPI, Finnhub, Benzinga, etc.) without touching the agent — the
agent only depends on the returned list-of-dicts contract.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def get_recent_news(symbol: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Return a list of recent news items: {headline, publisher, link, published}."""
    try:
        import yfinance as yf

        raw = yf.Ticker(symbol).news or []
        items: List[Dict[str, Any]] = []
        for entry in raw[:limit]:
            # yfinance schema varies; support both flat and nested ("content") forms.
            content = entry.get("content", entry)
            ts = entry.get("providerPublishTime")
            published = (
                datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                if isinstance(ts, (int, float))
                else content.get("pubDate", "")
            )
            items.append(
                {
                    "headline": content.get("title") or entry.get("title", ""),
                    "publisher": (content.get("provider") or {}).get("displayName")
                    or entry.get("publisher", "Unknown"),
                    "link": content.get("canonicalUrl", {}).get("url")
                    or entry.get("link", ""),
                    "published": published,
                }
            )
        return [i for i in items if i["headline"]]
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_recent_news(%s) failed: %s", symbol, exc)
        return []

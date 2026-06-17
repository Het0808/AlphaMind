"""LLM factory.

All agents obtain their model through this single factory so that the model,
temperature, timeout and retry policy are configured in exactly one place.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from .config import get_settings


def get_llm(temperature: float | None = None, *, model: str | None = None) -> ChatOpenAI:
    """Return a configured ChatOpenAI client.

    Args:
        temperature: Override the default sampling temperature for this call.
        model: Override the configured model (e.g. a cheaper one for routing).
    """
    settings = get_settings()
    return ChatOpenAI(
        model=model or settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=settings.openai_temperature if temperature is None else temperature,
        timeout=settings.request_timeout,
        max_retries=2,
    )

"""Contracts for ticker resolution."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class TickerSuggestion(BaseModel):
    company_name: str
    ticker: str


class TickerResolution(BaseModel):
    query: str = Field(..., description="The original user input.")
    ticker: str = Field(..., description="Canonical, validated ticker symbol.")
    company_name: str
    exchange: str = Field("US", description="NASDAQ/NYSE (US), NSE/BSE (India), or US/Unknown.")
    region: str = Field("US", description="US | IN | Unknown.")
    matched_by: str = Field(..., description="How it matched: alias | name | symbol.")

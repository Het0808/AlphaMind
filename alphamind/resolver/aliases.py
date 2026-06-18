"""Static company → ticker registry (US + Indian markets) and lookup index.

This is the offline, deterministic backbone of resolution. It can be extended, or
augmented at runtime by a provider lookup (see resolver.py), but it guarantees the
required mappings work with no network.

Each entry: (ticker, company_name, [aliases...], region).
"""

from __future__ import annotations

from typing import Dict, List, Tuple

# region: "US" or "IN"
COMPANIES: List[Tuple[str, str, List[str], str]] = [
    # ── United States ──
    ("AAPL", "Apple Inc.", ["apple"], "US"),
    ("MSFT", "Microsoft Corporation", ["microsoft"], "US"),
    ("TSLA", "Tesla, Inc.", ["tesla"], "US"),
    ("NVDA", "NVIDIA Corporation", ["nvidia"], "US"),
    ("GOOGL", "Alphabet Inc.", ["google", "alphabet"], "US"),
    ("AMZN", "Amazon.com, Inc.", ["amazon"], "US"),
    ("META", "Meta Platforms, Inc.", ["meta", "facebook"], "US"),
    ("AMD", "Advanced Micro Devices, Inc.", ["amd"], "US"),
    ("INTC", "Intel Corporation", ["intel"], "US"),
    ("NFLX", "Netflix, Inc.", ["netflix"], "US"),
    ("JPM", "JPMorgan Chase & Co.", ["jpmorgan", "jp morgan", "chase"], "US"),
    ("V", "Visa Inc.", ["visa"], "US"),
    ("DIS", "The Walt Disney Company", ["disney", "walt disney"], "US"),
    ("KO", "The Coca-Cola Company", ["coca cola", "coca-cola", "coke"], "US"),
    ("JNJ", "Johnson & Johnson", ["johnson & johnson", "johnson and johnson", "jnj"], "US"),
    ("XOM", "Exxon Mobil Corporation", ["exxon", "exxon mobil"], "US"),
    # ── India (NSE; .NS suffix for Yahoo/data providers) ──
    ("RELIANCE.NS", "Reliance Industries Limited", ["reliance", "reliance industries"], "IN"),
    ("INFY.NS", "Infosys Limited", ["infosys"], "IN"),
    ("TCS.NS", "Tata Consultancy Services Limited", ["tcs", "tata consultancy services"], "IN"),
    ("HDFCBANK.NS", "HDFC Bank Limited", ["hdfc", "hdfc bank"], "IN"),
    ("ICICIBANK.NS", "ICICI Bank Limited", ["icici", "icici bank"], "IN"),
    ("SBIN.NS", "State Bank of India", ["sbi", "state bank of india"], "IN"),
    ("WIPRO.NS", "Wipro Limited", ["wipro"], "IN"),
    ("TATAMOTORS.NS", "Tata Motors Limited", ["tata motors"], "IN"),
    ("HINDUNILVR.NS", "Hindustan Unilever Limited", ["hul", "hindustan unilever"], "IN"),
    ("BHARTIARTL.NS", "Bharti Airtel Limited", ["airtel", "bharti airtel"], "IN"),
    ("ADANIENT.NS", "Adani Enterprises Limited", ["adani", "adani enterprises"], "IN"),
]

# ── Derived indexes ──
TICKER_TO_NAME: Dict[str, str] = {t: name for t, name, _, _ in COMPANIES}
TICKER_TO_REGION: Dict[str, str] = {t: region for t, _, _, region in COMPANIES}

# alias (lowercased) -> ticker. Includes company names, explicit aliases, the
# ticker itself, and the Indian base symbol without the .NS/.BO suffix.
ALIAS_TO_TICKER: Dict[str, str] = {}
for _t, _name, _aliases, _region in COMPANIES:
    keys = set(_aliases) | {_name.lower(), _t.lower()}
    base = _t.split(".")[0].lower()
    keys.add(base)
    for k in keys:
        ALIAS_TO_TICKER.setdefault(k, _t)

# Human-readable name list for fuzzy suggestions.
ALIAS_NAMES: List[str] = sorted({_name for _, _name, _, _ in COMPANIES})

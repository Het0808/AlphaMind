"""Parse 10-K / 10-Q filings and extract the narrative sections we care about:
Risk Factors (Item 1A) and Management's Discussion & Analysis (Item 7 in a 10-K,
Item 2 in a 10-Q).

EDGAR filings are messy iXBRL HTML, and the item headers also appear in the table
of contents. The extractor finds every candidate start position for an item and
keeps the one with the longest body before the next item marker — the TOC entry
is tiny (the next item header follows immediately), so the real section wins.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

# Minimum characters for an extracted section to be considered real (filters TOC).
MIN_SECTION_CHARS = 500

# Per-form regex config: how to find the start of each section and where it ends.
# Patterns run against lower-cased, whitespace-collapsed text.
_SECTIONS = {
    "10-K": {
        "Item 1A Risk Factors": {
            "start": [r"item\s*1a[\.\)\:\s]+risk\s*factors"],
            "end": [r"item\s*1b[\.\)\:\s]", r"item\s*2[\.\)\:\s]+propert", r"item\s*3[\.\)\:\s]+legal"],
        },
        "Item 7 Management's Discussion & Analysis": {
            "start": [r"item\s*7[\.\)\:\s]+management.?s\s*discussion"],
            "end": [r"item\s*7a[\.\)\:\s]", r"item\s*8[\.\)\:\s]+financial\s*statements"],
        },
    },
    "10-Q": {
        "Item 1A Risk Factors": {
            "start": [r"item\s*1a[\.\)\:\s]+risk\s*factors"],
            "end": [r"item\s*2[\.\)\:\s]", r"item\s*3[\.\)\:\s]", r"item\s*4[\.\)\:\s]",
                    r"item\s*5[\.\)\:\s]", r"item\s*6[\.\)\:\s]"],
        },
        "Item 2 Management's Discussion & Analysis": {
            "start": [r"item\s*2[\.\)\:\s]+management.?s\s*discussion"],
            "end": [r"item\s*3[\.\)\:\s]+quantitative", r"item\s*4[\.\)\:\s]+controls"],
        },
    },
}


def normalize_form(form: str) -> str:
    """Map e.g. '10-K/A' → '10-K'."""
    f = (form or "").upper().strip()
    if f.startswith("10-K"):
        return "10-K"
    if f.startswith("10-Q"):
        return "10-Q"
    return f


def html_to_text(html: str) -> str:
    """Convert filing HTML to clean, whitespace-collapsed plain text."""
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("beautifulsoup4 is required to parse filings") from exc

    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:  # lxml not installed → stdlib parser
        soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return collapse_whitespace(text)


def collapse_whitespace(text: str) -> str:
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def extract_section(text: str, start_patterns: List[str], end_patterns: List[str]) -> Optional[str]:
    """Return the best (longest) body slice for a section, or None if not found."""
    lower = text.lower()
    starts = sorted({m.start() for p in start_patterns for m in re.finditer(p, lower)})
    if not starts:
        return None

    best: Optional[str] = None
    for s in starts:
        # Search for the next section boundary after a small offset past the header.
        scan_from = s + 40
        ends = [scan_from + m.start() for p in end_patterns
                for m in [re.search(p, lower[scan_from:])] if m]
        end = min(ends) if ends else len(text)
        segment = text[s:end].strip()
        if best is None or len(segment) > len(best):
            best = segment
    return best


def extract_sections(html_or_text: str, form: str, *, is_html: bool = True) -> Tuple[str, Dict[str, str]]:
    """Extract the target sections for a filing.

    Returns (full_text, {section_name: section_text}). Sections shorter than
    MIN_SECTION_CHARS are dropped as likely table-of-contents false positives.
    """
    text = html_to_text(html_or_text) if is_html else collapse_whitespace(html_or_text)
    config = _SECTIONS.get(normalize_form(form), {})

    sections: Dict[str, str] = {}
    for name, cfg in config.items():
        segment = extract_section(text, cfg["start"], cfg["end"])
        if segment and len(segment) >= MIN_SECTION_CHARS:
            sections[name] = segment
    return text, sections

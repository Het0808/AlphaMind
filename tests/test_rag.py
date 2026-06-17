"""Offline tests for the RAG layer's parsing and citation logic.

These exercise the trickiest, most failure-prone part — pulling the real Item 1A
and MD&A bodies out of a filing while ignoring the table of contents — without
any network, embeddings or Qdrant.
"""

from alphamind.rag.parser import extract_section, extract_sections, normalize_form
from alphamind.rag.schemas import Citation

RISK_BODY = (
    "Our business faces numerous risks including intense competition, regulatory "
    "change, supply chain disruption, and foreign currency exposure that could "
    "materially affect our results. " * 10
)
MDNA_BODY = (
    "Revenue increased year over year driven by strong product demand and new "
    "services, while gross margin expanded on favorable mix and operating leverage. " * 10
)

FILING = (
    "TABLE OF CONTENTS "
    "Item 1. Business 1 "
    "Item 1A. Risk Factors 12 "
    "Item 1B. Unresolved Staff Comments 25 "
    "Item 2. Properties 26 "
    "Item 7. Management's Discussion and Analysis 30 "
    "Item 7A. Quantitative and Qualitative Disclosures 45 "
    "Item 8. Financial Statements 46 "
    "PART I "
    "Item 1A. Risk Factors. " + RISK_BODY +
    " Item 1B. Unresolved Staff Comments. None. "
    "Item 2. Properties. We lease offices globally. "
    "Item 7. Management's Discussion and Analysis of Financial Condition and "
    "Results of Operations. " + MDNA_BODY +
    " Item 7A. Quantitative and Qualitative Disclosures About Market Risk. "
)


def test_normalize_form():
    assert normalize_form("10-K/A") == "10-K"
    assert normalize_form("10-q") == "10-Q"


def test_extract_section_prefers_body_over_toc():
    section = extract_section(
        FILING,
        start_patterns=[r"item\s*1a[\.\)\:\s]+risk\s*factors"],
        end_patterns=[r"item\s*1b[\.\)\:\s]"],
    )
    assert section is not None
    assert "intense competition" in section
    # The TOC entry "Item 1A. Risk Factors 12 Item 1B" must not be what we kept.
    assert len(section) > 500


def test_extract_sections_10k_finds_both():
    _, sections = extract_sections(FILING, "10-K", is_html=False)
    assert set(sections) == {
        "Item 1A Risk Factors",
        "Item 7 Management's Discussion & Analysis",
    }
    assert "supply chain disruption" in sections["Item 1A Risk Factors"]
    assert "gross margin expanded" in sections["Item 7 Management's Discussion & Analysis"]


def test_short_toc_only_yields_no_sections():
    toc_only = (
        "TABLE OF CONTENTS Item 1A. Risk Factors 12 Item 1B. Unresolved 25 "
        "Item 7. Management's Discussion and Analysis 30 Item 7A. Disclosures 45"
    )
    _, sections = extract_sections(toc_only, "10-K", is_html=False)
    assert sections == {}  # nothing exceeds MIN_SECTION_CHARS


def test_citation_reference_is_exact():
    c = Citation(
        ticker="AAPL",
        company="Apple Inc.",
        form="10-K",
        section="Item 1A Risk Factors",
        accession="0000320193-24-000123",
        filing_date="2024-11-01",
        url="https://www.sec.gov/Archives/edgar/data/320193/.../aapl.htm",
    )
    ref = c.reference()
    assert "Apple Inc. 10-K filed 2024-11-01" in ref
    assert "accession 0000320193-24-000123" in ref
    assert "Item 1A Risk Factors" in ref

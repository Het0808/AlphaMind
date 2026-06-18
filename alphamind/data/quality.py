"""Cross-source verification, confidence scoring and the fail-safe decision.

Confidence per field combines:
  • source authority   — audited SEC/EDGAR > FMP > Yahoo > unknown.
  • cross-source agreement — do independent providers report the same value?
  • validation         — range/cross-field issues penalize confidence.

Fields whose confidence falls below the configured threshold are nulled out so the
UI shows "Data unavailable" rather than an unverified number.
"""

from __future__ import annotations

import statistics
from typing import Dict, List, Optional

from .schemas import FieldQuality, NUMERIC_METRIC_FIELDS, QualityReport
from .validation import ValidationIssue, unit_of

# How much to trust a single source on its own (0..1).
SOURCE_AUTHORITY = {
    "sec_edgar": 0.85,
    "fmp": 0.72,
    "yahoo": 0.66,
}
_DEFAULT_AUTHORITY = 0.6


def agreement_score(values: List[float], tolerance: float) -> Optional[float]:
    """0..1 cross-source agreement from the relative spread of values."""
    vals = [v for v in values if isinstance(v, (int, float))]
    if len(vals) < 2:
        return None
    med = statistics.median(vals)
    if med == 0:
        spread = max(abs(v) for v in vals)
        return 1.0 if spread == 0 else 0.0
    spread = (max(vals) - min(vals)) / abs(med)
    # spread <= tolerance → ~1.0; spread >= 5×tolerance → ~0.0
    return max(0.0, min(1.0, 1.0 - spread / (5 * tolerance)))


def field_confidence(
    sources: Dict[str, float], agreement: Optional[float], has_error: bool, has_warning: bool,
) -> float:
    if not sources:
        return 0.0
    base = max(SOURCE_AUTHORITY.get(s, _DEFAULT_AUTHORITY) for s in sources)
    conf = base
    if agreement is not None:  # 2+ sources
        if agreement >= 0.9:
            conf = min(0.98, base + 0.12)      # corroborated
        elif agreement < 0.5:
            conf = base * 0.65                  # providers disagree → shown but flagged
        else:
            conf = base * 0.85
    if has_error:
        conf *= 0.35
    elif has_warning:
        conf *= 0.8
    return round(max(0.0, min(1.0, conf)), 3)


def build_quality(
    *,
    ticker: str,
    chosen: Dict[str, float],
    candidates: Dict[str, Dict[str, float]],
    field_sources: Dict[str, str],
    currency: Optional[str],
    issues: List[ValidationIssue],
    providers: List[str],
    tolerance: float,
    threshold: float,
    last_updated: str,
) -> QualityReport:
    """Assemble a QualityReport and return it (caller applies the fail-safe)."""
    issues_by_field: Dict[str, List[ValidationIssue]] = {}
    for iss in issues:
        issues_by_field.setdefault(iss.field, []).append(iss)

    field_quality: Dict[str, FieldQuality] = {}
    confidences: List[float] = []

    for field in NUMERIC_METRIC_FIELDS:
        srcs = {p: v for p, v in candidates.get(field, {}).items() if isinstance(v, (int, float))}
        value = chosen.get(field)
        fissues = issues_by_field.get(field, [])
        has_error = any(i.severity == "error" for i in fissues)
        has_warning = any(i.severity == "warning" for i in fissues)
        agreement = agreement_score(list(srcs.values()), tolerance)
        confidence = field_confidence(srcs, agreement, has_error, has_warning) if value is not None else 0.0

        if value is None:
            status = "unavailable"
        elif has_error:
            status = "out_of_range"
        elif agreement is not None and agreement < 0.5:
            status = "disagreement"
        elif len(srcs) >= 2:
            status = "ok"
        else:
            status = "single_source"

        field_quality[field] = FieldQuality(
            field=field, value=value, unit=unit_of(field), currency=currency if unit_of(field) == "currency" else None,
            sources=srcs, chosen_source=field_sources.get(field),
            agreement=agreement, confidence=confidence, status=status,
            issues=[i.message for i in fissues],
        )
        if value is not None:
            confidences.append(confidence)

    overall = round(statistics.mean(confidences), 3) if confidences else 0.0
    return QualityReport(
        overall_confidence=overall,
        providers=providers,
        field_quality=field_quality,
        validations=[f"[{i.severity}] {i.field}: {i.message}" for i in issues],
        last_updated=last_updated,
    )


def apply_fail_safe(metrics, quality: QualityReport, threshold: float) -> List[str]:
    """Null out fields below the confidence threshold. Returns the dropped fields."""
    dropped = []
    for field, fq in quality.field_quality.items():
        if fq.value is not None and fq.confidence < threshold:
            setattr(metrics, field, None)
            fq.status = "unavailable"
            dropped.append(field)
    return dropped

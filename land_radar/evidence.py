from __future__ import annotations

from datetime import date

from .models import Evidence


def point_in_time_safe(evidence: Evidence, cutoff: date) -> bool:
    """True only when the evidence was knowable at the requested cutoff."""
    if evidence.published_date and evidence.published_date > cutoff:
        return False
    if evidence.effective_date and evidence.effective_date > cutoff:
        return False
    if evidence.observed_date and evidence.observed_date > cutoff:
        return False
    return True


def evidence_confidence(evidence: list[Evidence]) -> float | None:
    if not evidence:
        return None
    return round(sum(item.confidence for item in evidence) / len(evidence), 2)


def filter_point_in_time(evidence: list[Evidence], cutoff: date) -> list[Evidence]:
    return [item for item in evidence if point_in_time_safe(item, cutoff)]

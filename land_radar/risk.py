from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Iterable

from .evidence import evidence_confidence
from .models import Evidence, HardRiskFlags


class RiskSeverity(IntEnum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class RiskFinding:
    category: str
    severity: RiskSeverity
    note: str = ""
    hard_veto: bool = False
    evidence: list[Evidence] = field(default_factory=list)

    def validate(self) -> None:
        if not self.category.strip():
            raise ValueError("Risk category cannot be empty")
        if self.severity > RiskSeverity.NONE and not self.evidence:
            raise ValueError("Non-zero risk findings require evidence")
        if self.hard_veto and not self.evidence:
            raise ValueError("Hard-veto findings require evidence")

    @property
    def evidence_confidence(self) -> float | None:
        return evidence_confidence(self.evidence)


@dataclass(frozen=True)
class RiskSummary:
    finding_count: int
    hard_veto: bool
    hard_veto_categories: tuple[str, ...]
    max_severity: RiskSeverity
    average_evidence_confidence: float | None


def summarize_risks(findings: Iterable[RiskFinding]) -> RiskSummary:
    items = list(findings)
    for item in items:
        item.validate()

    if not items:
        return RiskSummary(
            finding_count=0,
            hard_veto=False,
            hard_veto_categories=tuple(),
            max_severity=RiskSeverity.NONE,
            average_evidence_confidence=None,
        )

    veto_categories = tuple(
        item.category
        for item in items
        if item.hard_veto
    )
    confidences = [
        item.evidence_confidence
        for item in items
        if item.evidence_confidence is not None
    ]

    return RiskSummary(
        finding_count=len(items),
        hard_veto=bool(veto_categories),
        hard_veto_categories=veto_categories,
        max_severity=max(item.severity for item in items),
        average_evidence_confidence=(
            round(sum(confidences) / len(confidences), 2)
            if confidences
            else None
        ),
    )


def to_legacy_hard_flags(findings: Iterable[RiskFinding]) -> HardRiskFlags:
    """Bridge explicit veto findings into the current scoring veto interface.

    Categories that do not map cleanly remain visible in RiskSummary and are
    not silently forced into an unrelated legacy flag.
    """
    items = [item for item in findings if item.hard_veto]
    categories = {item.category for item in items}

    return HardRiskFlags(
        legal_restriction="legal_restriction" in categories,
        severe_flood="flood" in categories,
        severe_landslide="landslide" in categories,
        no_legal_access="no_legal_access" in categories,
    )

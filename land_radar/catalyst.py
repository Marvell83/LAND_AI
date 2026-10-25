from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Iterable

from .evidence import evidence_confidence
from .models import Evidence


class CatalystStage(IntEnum):
    NONE_OR_RUMOR = 0
    OFFICIAL_INTENT = 1
    PLAN_OR_APPROVAL = 2
    BUDGET_OR_TENDER = 3
    CONSTRUCTION_STARTED = 4
    COMPLETED = 5
    MEASURABLE_EFFECT = 6


STAGE_LABELS = {
    CatalystStage.NONE_OR_RUMOR: "Yok / söylenti",
    CatalystStage.OFFICIAL_INTENT: "Resmî niyet / strateji",
    CatalystStage.PLAN_OR_APPROVAL: "Plan / onay",
    CatalystStage.BUDGET_OR_TENDER: "Bütçe / ihale",
    CatalystStage.CONSTRUCTION_STARTED: "Yapım başladı",
    CatalystStage.COMPLETED: "Tamamlandı",
    CatalystStage.MEASURABLE_EFFECT: "Ölçülebilir ekonomik etki",
}


@dataclass
class Catalyst:
    catalyst_id: str
    name: str
    category: str
    stage: CatalystStage = CatalystStage.NONE_OR_RUMOR
    distance_km: float | None = None
    evidence: list[Evidence] = field(default_factory=list)

    def validate(self) -> None:
        if self.distance_km is not None and self.distance_km < 0:
            raise ValueError("distance_km cannot be negative")
        if self.stage > CatalystStage.NONE_OR_RUMOR and not self.evidence:
            raise ValueError(
                "Catalyst stages above NONE_OR_RUMOR require at least one evidence item"
            )

    @property
    def completion_ratio(self) -> float:
        return round(int(self.stage) / int(CatalystStage.MEASURABLE_EFFECT), 4)

    @property
    def evidence_confidence(self) -> float | None:
        return evidence_confidence(self.evidence)


@dataclass(frozen=True)
class CatalystSummary:
    catalyst_count: int
    evidenced_count: int
    active_count: int
    completed_or_effect_count: int
    average_completion_ratio: float | None
    average_evidence_confidence: float | None


def summarize_catalysts(catalysts: Iterable[Catalyst]) -> CatalystSummary:
    items = list(catalysts)
    for item in items:
        item.validate()

    if not items:
        return CatalystSummary(
            catalyst_count=0,
            evidenced_count=0,
            active_count=0,
            completed_or_effect_count=0,
            average_completion_ratio=None,
            average_evidence_confidence=None,
        )

    evidenced = [c for c in items if c.evidence]
    active = [c for c in items if c.stage >= CatalystStage.PLAN_OR_APPROVAL]
    completed = [c for c in items if c.stage >= CatalystStage.COMPLETED]
    confidences = [
        c.evidence_confidence
        for c in evidenced
        if c.evidence_confidence is not None
    ]

    return CatalystSummary(
        catalyst_count=len(items),
        evidenced_count=len(evidenced),
        active_count=len(active),
        completed_or_effect_count=len(completed),
        average_completion_ratio=round(
            sum(c.completion_ratio for c in items) / len(items),
            4,
        ),
        average_evidence_confidence=(
            round(sum(confidences) / len(confidences), 2)
            if confidences
            else None
        ),
    )


def missing_required_categories(
    catalysts: Iterable[Catalyst],
    required_categories: Iterable[str],
    *,
    minimum_stage: CatalystStage = CatalystStage.PLAN_OR_APPROVAL,
) -> tuple[str, ...]:
    items = list(catalysts)
    present = {
        c.category
        for c in items
        if c.stage >= minimum_stage and c.evidence
    }
    return tuple(
        category
        for category in required_categories
        if category not in present
    )

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import IntEnum
from typing import Any


class PlanStage(IntEnum):
    UNKNOWN = 0
    PROPOSAL = 1
    SUBMITTED = 2
    APPROVED = 3
    ON_SUSPENSION = 4
    OBJECTION_REVIEW = 5
    FINALIZED = 6
    CANCELLED = 7


@dataclass(frozen=True)
class PlanEvidence:
    plan_id: str
    title: str
    plan_type: str
    stage: PlanStage
    source: str
    source_url: str
    scale_denominator: int | None = None
    published_date: date | None = None
    decision_date: date | None = None
    effective_date: date | None = None
    suspension_start: date | None = None
    suspension_end: date | None = None
    observed_date: date | None = None
    confidence: float = 50.0
    geometry_verified: bool = False
    note: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.plan_id.strip():
            raise ValueError("plan_id cannot be empty")
        if not self.title.strip():
            raise ValueError("plan title cannot be empty")
        if not self.plan_type.strip():
            raise ValueError("plan_type cannot be empty")
        if not self.source.strip() or not self.source_url.strip():
            raise ValueError("plan source and source_url are required")
        if not 0 <= float(self.confidence) <= 100:
            raise ValueError("plan confidence must be between 0 and 100")
        if self.scale_denominator is not None and self.scale_denominator <= 0:
            raise ValueError("scale_denominator must be positive")
        if (
            self.suspension_start is not None
            and self.suspension_end is not None
            and self.suspension_start > self.suspension_end
        ):
            raise ValueError("suspension_start cannot be after suspension_end")

    @property
    def is_final(self) -> bool:
        return self.stage == PlanStage.FINALIZED

    @property
    def is_cancelled(self) -> bool:
        return self.stage == PlanStage.CANCELLED


def stage_from_text(value: str) -> PlanStage:
    text = " ".join(str(value or "").casefold().split())
    mapping = (
        (("iptal", "cancel"), PlanStage.CANCELLED),
        (("kesin", "final"), PlanStage.FINALIZED),
        (("itiraz",), PlanStage.OBJECTION_REVIEW),
        (("askı", "aski", "suspension"), PlanStage.ON_SUSPENSION),
        (("onay", "approved"), PlanStage.APPROVED),
        (("kuruma ilet", "submitted"), PlanStage.SUBMITTED),
        (("teklif", "proposal"), PlanStage.PROPOSAL),
    )
    for needles, stage in mapping:
        if any(needle in text for needle in needles):
            return stage
    return PlanStage.UNKNOWN


def plan_type_normalized(value: str) -> str:
    text = str(value or "").strip().upper()
    aliases = {
        "UİP": "UIP",
        "UİP-": "UIP",
        "UYGULAMA İMAR PLANI": "UIP",
        "NİP": "NIP",
        "NAZIM İMAR PLANI": "NIP",
        "ÇDP": "CDP",
        "ÇEVRE DÜZENİ PLANI": "CDP",
    }
    return aliases.get(text, text.replace("İ", "I").replace("Ç", "C"))

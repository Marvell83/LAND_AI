from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import IntEnum
from typing import Any

from .spatial.geometry import geometry_from_geojson


class LegalEffect(IntEnum):
    CONTEXT = 0
    REVIEW_REQUIRED = 1
    RESTRICTIVE = 2
    PROHIBITED = 3


@dataclass(frozen=True)
class PlanningConstraint:
    constraint_id: str
    category: str
    geometry_geojson: dict[str, Any]
    source: str
    legal_effect: LegalEffect = LegalEffect.REVIEW_REQUIRED
    observed_date: date | None = None
    effective_date: date | None = None
    source_url: str | None = None
    hard_veto: bool = False
    confidence: float = 50.0
    note: str = ""
    properties: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.constraint_id.strip():
            raise ValueError("constraint_id cannot be empty")
        if not self.category.strip():
            raise ValueError("constraint category cannot be empty")
        if not self.source.strip():
            raise ValueError("constraint source cannot be empty")
        if not 0 <= float(self.confidence) <= 100:
            raise ValueError("constraint confidence must be between 0 and 100")
        geometry = geometry_from_geojson(self.geometry_geojson)
        if geometry.is_empty:
            raise ValueError("constraint geometry cannot be empty")

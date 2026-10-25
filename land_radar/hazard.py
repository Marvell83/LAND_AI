from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import IntEnum
from typing import Any

from .spatial.geometry import geometry_from_geojson


class HazardSeverity(IntEnum):
    UNKNOWN = -1
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass(frozen=True)
class HazardGeometry:
    hazard_id: str
    category: str
    severity: HazardSeverity
    geometry_geojson: dict[str, Any]
    source: str
    observed_date: date | None = None
    source_url: str | None = None
    hard_veto: bool = False
    confidence: float = 50.0
    note: str = ""

    def __post_init__(self) -> None:
        if not self.hazard_id.strip():
            raise ValueError("hazard_id cannot be empty")
        if not self.category.strip():
            raise ValueError("hazard category cannot be empty")
        if not self.source.strip():
            raise ValueError("hazard source cannot be empty")
        if not 0 <= float(self.confidence) <= 100:
            raise ValueError("hazard confidence must be between 0 and 100")
        geometry = geometry_from_geojson(self.geometry_geojson)
        if geometry.is_empty:
            raise ValueError("hazard geometry cannot be empty")

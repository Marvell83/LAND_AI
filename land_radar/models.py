from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


def clamp_score(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


@dataclass(frozen=True)
class Evidence:
    source: str
    claim: str
    observed_date: Optional[date] = None
    published_date: Optional[date] = None
    effective_date: Optional[date] = None
    url: Optional[str] = None
    confidence: float = 50.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "confidence", clamp_score(self.confidence))


@dataclass
class HardRiskFlags:
    legal_restriction: bool = False
    severe_flood: bool = False
    severe_landslide: bool = False
    no_legal_access: bool = False

    @property
    def blocked(self) -> bool:
        return any(
            (
                self.legal_restriction,
                self.severe_flood,
                self.severe_landslide,
                self.no_legal_access,
            )
        )

    def reasons(self) -> list[str]:
        labels = {
            "legal_restriction": "Kritik hukuki kısıt",
            "severe_flood": "Çok yüksek taşkın riski",
            "severe_landslide": "Çok yüksek heyelan riski",
            "no_legal_access": "Hukuki yol erişimi yok",
        }
        return [labels[name] for name, value in vars(self).items() if value]


@dataclass
class CellMetrics:
    urban_pressure: Optional[float] = None
    development_acceleration: Optional[float] = None
    catalyst_maturity: Optional[float] = None
    story_maturity: Optional[float] = None
    physical_quality: Optional[float] = None
    mispricing: Optional[float] = None
    exit_demand: Optional[float] = None
    risk: Optional[float] = None
    confidence: Optional[float] = None

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if value is not None:
                setattr(self, name, clamp_score(value))


@dataclass
class LandCell:
    cell_id: str
    center_lat: float
    center_lon: float
    metrics: CellMetrics = field(default_factory=CellMetrics)
    hard_risks: HardRiskFlags = field(default_factory=HardRiskFlags)
    evidence: list[Evidence] = field(default_factory=list)

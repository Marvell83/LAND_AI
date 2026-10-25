from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import LandCell


@dataclass(frozen=True)
class ScoreResult:
    blocked: bool
    block_reasons: tuple[str, ...]
    transition_score: Optional[float]
    research_priority_score: Optional[float]
    missing_metrics: tuple[str, ...]


_TRANSITION_WEIGHTS = {
    "urban_pressure": 0.30,
    "development_acceleration": 0.25,
    "catalyst_maturity": 0.20,
    "story_maturity": 0.15,
    "physical_quality": 0.10,
}

# Provisional research ranking only. These weights must be calibrated by backtest.
_PRIORITY_WEIGHTS = {
    "transition": 0.35,
    "mispricing": 0.25,
    "story_maturity": 0.15,
    "exit_demand": 0.10,
    "confidence": 0.15,
}


def _weighted_average(values: dict[str, Optional[float]], weights: dict[str, float]) -> Optional[float]:
    available = [(name, value) for name, value in values.items() if value is not None]
    if not available:
        return None

    total_weight = sum(weights[name] for name, _ in available)
    return sum(float(value) * weights[name] for name, value in available) / total_weight


def score_cell(cell: LandCell) -> ScoreResult:
    if cell.hard_risks.blocked:
        return ScoreResult(
            blocked=True,
            block_reasons=tuple(cell.hard_risks.reasons()),
            transition_score=None,
            research_priority_score=None,
            missing_metrics=tuple(),
        )

    m = cell.metrics
    transition = _weighted_average(
        {name: getattr(m, name) for name in _TRANSITION_WEIGHTS},
        _TRANSITION_WEIGHTS,
    )

    required_for_priority = {
        "mispricing": m.mispricing,
        "exit_demand": m.exit_demand,
        "confidence": m.confidence,
    }
    missing = tuple(name for name, value in required_for_priority.items() if value is None)

    priority = None
    if transition is not None and not missing:
        raw = (
            transition * _PRIORITY_WEIGHTS["transition"]
            + m.mispricing * _PRIORITY_WEIGHTS["mispricing"]
            + (m.story_maturity or 0.0) * _PRIORITY_WEIGHTS["story_maturity"]
            + m.exit_demand * _PRIORITY_WEIGHTS["exit_demand"]
            + m.confidence * _PRIORITY_WEIGHTS["confidence"]
        )
        if m.risk is not None:
            raw -= 0.30 * m.risk
        priority = max(0.0, min(100.0, raw))

    return ScoreResult(
        blocked=False,
        block_reasons=tuple(),
        transition_score=round(transition, 2) if transition is not None else None,
        research_priority_score=round(priority, 2) if priority is not None else None,
        missing_metrics=missing,
    )

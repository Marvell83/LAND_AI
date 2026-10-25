from datetime import date

import pytest

from land_radar.catalyst import (
    Catalyst,
    CatalystStage,
    missing_required_categories,
    summarize_catalysts,
)
from land_radar.models import Evidence


def _evidence(confidence: float = 80.0) -> Evidence:
    return Evidence(
        source="official",
        claim="approved",
        published_date=date(2025, 1, 1),
        confidence=confidence,
    )


def test_stage_requires_evidence():
    catalyst = Catalyst(
        catalyst_id="x",
        name="Road",
        category="road",
        stage=CatalystStage.PLAN_OR_APPROVAL,
    )
    with pytest.raises(ValueError):
        catalyst.validate()


def test_summary_counts_evidenced_active_and_completed():
    items = [
        Catalyst(
            catalyst_id="a",
            name="OSB",
            category="industrial",
            stage=CatalystStage.CONSTRUCTION_STARTED,
            evidence=[_evidence(90)],
        ),
        Catalyst(
            catalyst_id="b",
            name="Rail",
            category="rail",
            stage=CatalystStage.COMPLETED,
            evidence=[_evidence(70)],
        ),
        Catalyst(
            catalyst_id="c",
            name="Rumor",
            category="road",
            stage=CatalystStage.NONE_OR_RUMOR,
        ),
    ]
    result = summarize_catalysts(items)
    assert result.catalyst_count == 3
    assert result.evidenced_count == 2
    assert result.active_count == 2
    assert result.completed_or_effect_count == 1
    assert result.average_evidence_confidence == 80.0


def test_missing_required_categories():
    items = [
        Catalyst(
            catalyst_id="a",
            name="OSB",
            category="industrial",
            stage=CatalystStage.PLAN_OR_APPROVAL,
            evidence=[_evidence()],
        )
    ]
    missing = missing_required_categories(
        items,
        ["industrial", "road", "rail"],
    )
    assert missing == ("road", "rail")

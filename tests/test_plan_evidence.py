from datetime import date

from land_radar.plan_evidence import (
    PlanEvidence,
    PlanStage,
    plan_type_normalized,
    stage_from_text,
)
from land_radar.plan_registry import filter_point_in_time


def _plan(stage=PlanStage.FINALIZED, published=date(2026, 1, 1)):
    return PlanEvidence(
        plan_id="UIP-123",
        title="Test plan",
        plan_type="UİP",
        stage=stage,
        source="e-Plan",
        source_url="https://e-plan.gov.tr/",
        scale_denominator=1000,
        published_date=published,
        confidence=95,
    )


def test_plan_stage_mapping():
    assert stage_from_text("askıdaki plan") == PlanStage.ON_SUSPENSION
    assert stage_from_text("kesinleşmiş plan") == PlanStage.FINALIZED
    assert stage_from_text("iptal edildi") == PlanStage.CANCELLED


def test_plan_type_normalization():
    assert plan_type_normalized("UİP") == "UIP"
    assert plan_type_normalized("NAZIM İMAR PLANI") == "NIP"
    assert plan_type_normalized("ÇDP") == "CDP"


def test_point_in_time_excludes_future_evidence():
    plans = [
        _plan(published=date(2025, 1, 1)),
        PlanEvidence(
            plan_id="NIP-999",
            title="Future",
            plan_type="NIP",
            stage=PlanStage.APPROVED,
            source="official",
            source_url="https://example.gov.tr",
            published_date=date(2027, 1, 1),
        ),
    ]
    result = filter_point_in_time(
        plans,
        as_of_date=date(2026, 10, 25),
    )
    assert [plan.plan_id for plan in result] == ["UIP-123"]

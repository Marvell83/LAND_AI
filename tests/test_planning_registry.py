from datetime import date

from land_radar.planning import LegalEffect, PlanningConstraint
from land_radar.spatial.planning_registry import (
    constraints_from_feature_collection,
    constraints_to_feature_collection,
)


def test_planning_registry_roundtrip():
    constraint = PlanningConstraint(
        constraint_id="official:park:1",
        category="national_park",
        geometry_geojson={
            "type": "Point",
            "coordinates": [29.0, 40.0],
        },
        source="official",
        legal_effect=LegalEffect.REVIEW_REQUIRED,
        observed_date=date(2026, 10, 25),
        hard_veto=False,
        confidence=95,
        properties={"SITENAME": "Test"},
    )
    payload = constraints_to_feature_collection([constraint])
    restored = constraints_from_feature_collection(payload)

    assert len(restored) == 1
    assert restored[0].constraint_id == "official:park:1"
    assert restored[0].legal_effect == LegalEffect.REVIEW_REQUIRED
    assert restored[0].properties["SITENAME"] == "Test"

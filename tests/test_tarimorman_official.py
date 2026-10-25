from datetime import date

from land_radar.hazard import HazardSeverity
from land_radar.planning import LegalEffect
from land_radar.providers.tarimorman_official import (
    PROTECTED_LAYERS,
    feature_to_flood_hazard,
    feature_to_protected_constraint,
    flood_severity_from_properties,
)


def _polygon():
    return {
        "type": "Polygon",
        "coordinates": [[
            [29.0, 40.0],
            [29.1, 40.0],
            [29.1, 40.1],
            [29.0, 40.1],
            [29.0, 40.0],
        ]],
    }


def test_protected_feature_requires_review_not_auto_veto():
    feature = {
        "type": "Feature",
        "geometry": _polygon(),
        "properties": {
            "OBJECTID": 7,
            "SITENAME": "Örnek Milli Park",
        },
    }
    constraint = feature_to_protected_constraint(
        feature,
        PROTECTED_LAYERS[0],
        observed_date=date(2026, 10, 25),
    )
    assert constraint is not None
    assert constraint.legal_effect == LegalEffect.REVIEW_REQUIRED
    assert constraint.hard_veto is False
    assert constraint.confidence == 95.0


def test_flood_text_severity_mapping_is_conservative():
    assert flood_severity_from_properties({"KATEGORI": "Çok Yüksek"}) == HazardSeverity.CRITICAL
    assert flood_severity_from_properties({"KATEGORI": "Yüksek"}) == HazardSeverity.HIGH
    assert flood_severity_from_properties({"KATEGORI": "Orta"}) == HazardSeverity.MEDIUM
    assert flood_severity_from_properties({"KATEGORI": "Düşük"}) == HazardSeverity.LOW
    assert flood_severity_from_properties({"KATEGORI": "Belirsiz"}) == HazardSeverity.UNKNOWN


def test_flood_feature_never_auto_vetoes():
    feature = {
        "type": "Feature",
        "geometry": _polygon(),
        "properties": {
            "OBJECTID": 11,
            "ALAN_ADI": "Örnek",
            "KATEGORI": "Yüksek",
            "RISK100_ENUM": 3,
        },
    }
    hazard = feature_to_flood_hazard(
        feature,
        observed_date=date(2026, 10, 25),
    )
    assert hazard is not None
    assert hazard.severity == HazardSeverity.HIGH
    assert hazard.hard_veto is False
    assert "RISK100_ENUM=3" in hazard.note

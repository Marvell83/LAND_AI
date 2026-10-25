from datetime import date

from land_radar.hazard import HazardGeometry, HazardSeverity
from land_radar.spatial.hazard_registry import (
    hazards_from_feature_collection,
    hazards_to_feature_collection,
)


def _hazard():
    return HazardGeometry(
        hazard_id="flood:test",
        category="flood",
        severity=HazardSeverity.HIGH,
        geometry_geojson={
            "type": "Polygon",
            "coordinates": [[
                [29.0, 40.0],
                [29.1, 40.0],
                [29.1, 40.1],
                [29.0, 40.1],
                [29.0, 40.0],
            ]],
        },
        source="USBS",
        observed_date=date(2026, 10, 25),
        hard_veto=False,
        confidence=90,
    )


def test_hazard_registry_roundtrip():
    payload = hazards_to_feature_collection([_hazard()])
    hazards = hazards_from_feature_collection(payload)
    assert len(hazards) == 1
    assert hazards[0].hazard_id == "flood:test"
    assert hazards[0].severity == HazardSeverity.HIGH
    assert hazards[0].source == "USBS"


def test_numeric_severity_supported():
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [29.0, 40.0]},
                "properties": {
                    "hazard_id": "x",
                    "category": "landslide",
                    "severity": 4,
                    "source": "AFAD",
                },
            }
        ],
    }
    hazards = hazards_from_feature_collection(payload)
    assert hazards[0].severity == HazardSeverity.CRITICAL

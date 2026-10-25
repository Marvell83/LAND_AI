from datetime import date

import pytest

from land_radar.spatial.geometry import GeometryEvidence, GeometryEvidenceError


def test_geometry_evidence_accepts_point():
    item = GeometryEvidence(
        source="OpenStreetMap",
        feature_name="Test OSB",
        geometry_geojson={"type": "Point", "coordinates": [29.0, 40.0]},
        observed_date=date(2026, 10, 25),
        confidence=60,
    )
    assert item.feature_name == "Test OSB"


def test_geometry_evidence_rejects_bad_confidence():
    with pytest.raises(GeometryEvidenceError):
        GeometryEvidence(
            source="OpenStreetMap",
            feature_name="X",
            geometry_geojson={"type": "Point", "coordinates": [29.0, 40.0]},
            confidence=120,
        )

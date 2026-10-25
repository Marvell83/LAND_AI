from datetime import date

from land_radar.spatial.geometry import GeometryEvidence
from land_radar.spatial.registry import (
    GeometryRegistryEntry,
    load_geometry_registry,
    registry_from_feature_collection,
    registry_to_feature_collection,
    save_geometry_registry,
)


def _entry():
    return GeometryRegistryEntry(
        catalyst_id="osb:test",
        evidence=GeometryEvidence(
            source="OpenStreetMap",
            feature_name="Test OSB",
            geometry_geojson={"type": "Point", "coordinates": [29.0, 40.0]},
            observed_date=date(2026, 10, 25),
            feature_id="osm:way:1",
            confidence=60,
            geometry_role="node_point",
        ),
        manual_verified=True,
    )


def test_registry_roundtrip_payload():
    payload = registry_to_feature_collection([_entry()])
    entries = registry_from_feature_collection(payload)
    assert len(entries) == 1
    assert entries[0].catalyst_id == "osb:test"
    assert entries[0].manual_verified is True
    assert entries[0].evidence.feature_id == "osm:way:1"


def test_registry_file_roundtrip(tmp_path):
    path = tmp_path / "registry.geojson"
    save_geometry_registry([_entry()], path)
    entries = load_geometry_registry(path)
    assert len(entries) == 1
    assert entries[0].evidence.feature_name == "Test OSB"

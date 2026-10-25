from datetime import date

from land_radar.catalyst import Catalyst, CatalystStage
from land_radar.grid import GridCell
from land_radar.models import Evidence
from land_radar.spatial.batch import batch_link_catalysts
from land_radar.spatial.geometry import GeometryEvidence
from land_radar.spatial.registry import GeometryRegistryEntry


def _catalyst():
    return Catalyst(
        catalyst_id="osb:test",
        name="Test OSB",
        category="industrial_osb",
        stage=CatalystStage.COMPLETED,
        evidence=[
            Evidence(
                source="OSBÜK",
                claim="Faaliyette",
                published_date=date(2026, 10, 1),
                confidence=90,
            )
        ],
    )


def _entry():
    return GeometryRegistryEntry(
        catalyst_id="osb:test",
        evidence=GeometryEvidence(
            source="OpenStreetMap",
            feature_name="Test OSB",
            geometry_geojson={"type": "Point", "coordinates": [29.1, 40.0]},
            confidence=60,
        ),
    )


def test_batch_link_and_distance_filter():
    cells = [
        GridCell(cell_id="A", center_lat=40.0, center_lon=29.0, size_km=5.0),
        GridCell(cell_id="B", center_lat=41.0, center_lon=30.0, size_km=5.0),
    ]
    result = batch_link_catalysts(
        cells,
        {"osb:test": _catalyst()},
        [_entry()],
        max_distance_km=20,
    )
    assert len(result.links) == 1
    assert result.links[0].cell_id == "A"
    assert result.missing_geometries == ()
    assert result.missing_catalysts == ()


def test_batch_reports_registry_mismatches():
    result = batch_link_catalysts(
        [GridCell(cell_id="A", center_lat=40.0, center_lon=29.0, size_km=5.0)],
        {"osb:known": Catalyst(catalyst_id="osb:known", name="Known", category="industrial")},
        [_entry()],
    )
    assert result.missing_catalysts == ("osb:test",)
    assert result.missing_geometries == ("osb:known",)

from datetime import date

from land_radar.catalyst import Catalyst, CatalystStage
from land_radar.grid import GridCell
from land_radar.models import Evidence
from land_radar.spatial.catalyst_geometry import link_catalyst_to_cell
from land_radar.spatial.geometry import GeometryEvidence


def test_status_and_geometry_confidence_remain_separate():
    catalyst = Catalyst(
        catalyst_id="osb:test",
        name="Test OSB",
        category="industrial_osb",
        stage=CatalystStage.CONSTRUCTION_STARTED,
        evidence=[
            Evidence(
                source="OSBÜK",
                claim="Altyapı hazırlanıyor",
                published_date=date(2026, 10, 1),
                confidence=90,
            )
        ],
    )
    geometry = GeometryEvidence(
        source="OpenStreetMap",
        feature_name="Test OSB",
        geometry_geojson={"type": "Point", "coordinates": [29.1, 40.0]},
        confidence=55,
    )
    cell = GridCell(cell_id="A", center_lat=40.0, center_lon=29.0, size_km=5.0)

    link = link_catalyst_to_cell(catalyst, geometry, cell)

    assert link.status_evidence_confidence == 90.0
    assert link.geometry_confidence == 55.0
    assert link.distance_km > 0
    assert link.evidence_complete is True

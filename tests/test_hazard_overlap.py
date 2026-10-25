from land_radar.grid import GridCell
from land_radar.hazard import HazardGeometry, HazardSeverity
from land_radar.spatial.hazard_overlap import (
    batch_link_hazards,
    link_hazard_to_cell,
    summarize_cell_hazards,
)


def _polygon(hard_veto: bool = False):
    return HazardGeometry(
        hazard_id="hazard:test",
        category="flood",
        severity=HazardSeverity.HIGH,
        geometry_geojson={
            "type": "Polygon",
            "coordinates": [[
                [28.99, 39.99],
                [29.01, 39.99],
                [29.01, 40.01],
                [28.99, 40.01],
                [28.99, 39.99],
            ]],
        },
        source="official",
        hard_veto=hard_veto,
        confidence=95,
    )


def test_hazard_intersection_produces_overlap():
    cell = GridCell(cell_id="A", center_lat=40.0, center_lon=29.0, size_km=5.0)
    link = link_hazard_to_cell(cell, _polygon())
    assert link.intersects_cell is True
    assert link.distance_km == 0.0
    assert 0 < link.overlap_ratio <= 1.0


def test_hard_veto_only_when_flagged_and_intersecting():
    cell = GridCell(cell_id="A", center_lat=40.0, center_lon=29.0, size_km=5.0)
    soft = link_hazard_to_cell(cell, _polygon(hard_veto=False))
    hard = link_hazard_to_cell(cell, _polygon(hard_veto=True))

    soft_summary = summarize_cell_hazards("A", [soft])
    hard_summary = summarize_cell_hazards("A", [hard])

    assert soft_summary.hard_veto is False
    assert hard_summary.hard_veto is True
    assert hard_summary.hard_veto_categories == ("flood",)


def test_batch_distance_filter():
    cells = [
        GridCell(cell_id="A", center_lat=40.0, center_lon=29.0, size_km=5.0),
        GridCell(cell_id="B", center_lat=41.0, center_lon=30.0, size_km=5.0),
    ]
    links = batch_link_hazards(cells, [_polygon()], max_distance_km=20)
    assert {link.cell_id for link in links} == {"A"}

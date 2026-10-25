from land_radar.grid import GridCell
from land_radar.spatial.distance import (
    distance_from_cell_to_geometry,
    distance_from_point_to_geometry,
)
from land_radar.spatial.geometry import GeometryEvidence


def _point(lon: float, lat: float) -> GeometryEvidence:
    return GeometryEvidence(
        source="test",
        feature_name="point",
        geometry_geojson={"type": "Point", "coordinates": [lon, lat]},
        confidence=100,
    )


def test_point_inside_cell_intersects():
    cell = GridCell(cell_id="A", center_lat=40.0, center_lon=29.0, size_km=5.0)
    result = distance_from_cell_to_geometry(cell, _point(29.0, 40.0))
    assert result.intersects_cell is True
    assert result.distance_km == 0.0


def test_point_outside_cell_has_metric_distance():
    cell = GridCell(cell_id="A", center_lat=40.0, center_lon=29.0, size_km=5.0)
    result = distance_from_cell_to_geometry(cell, _point(29.10, 40.0))
    assert result.intersects_cell is False
    assert 5.0 < result.distance_km < 8.0


def test_point_to_geometry_distance():
    distance = distance_from_point_to_geometry(40.0, 29.0, _point(29.1, 40.0))
    assert 8.0 < distance < 9.0

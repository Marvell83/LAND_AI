from land_radar.geometry import bbox_for_cell
from land_radar.grid import GridCell


def test_bbox_contains_center():
    cell = GridCell(cell_id="X", center_lat=40.0, center_lon=29.0, size_km=5.0)
    min_lon, min_lat, max_lon, max_lat = bbox_for_cell(cell)
    assert min_lon < 29.0 < max_lon
    assert min_lat < 40.0 < max_lat

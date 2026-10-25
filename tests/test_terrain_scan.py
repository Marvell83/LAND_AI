from pathlib import Path

from land_radar.grid import GridCell
from land_radar.providers.copernicus_dem import TerrainSummary
from land_radar.terrain_scan import rank_by_flatness, scan_terrain


class FakeClient:
    def __init__(self):
        self.calls = 0

    def terrain_summary(
        self,
        bbox,
        *,
        width=96,
        height=96,
        dem_instance="COPERNICUS_90",
    ):
        self.calls += 1
        return TerrainSummary(
            mean_elevation_m=100.0,
            min_elevation_m=90.0,
            max_elevation_m=120.0,
            mean_slope_deg=3.0,
            p90_slope_deg=5.0,
            max_slope_deg=9.0,
            valid_pixels=100,
            dem_instance=dem_instance,
        )


def test_terrain_scan_uses_cache(tmp_path: Path):
    cells = [
        GridCell(cell_id="A", center_lat=40.0, center_lon=29.0, size_km=5.0),
    ]
    client = FakeClient()

    first = scan_terrain(
        cells,
        client,
        cache_dir=tmp_path,
    )
    second = scan_terrain(
        cells,
        client,
        cache_dir=tmp_path,
    )

    assert client.calls == 1
    assert first[0].cache_hit is False
    assert second[0].cache_hit is True


def test_rank_by_flatness():
    client = FakeClient()
    cells = [
        GridCell(cell_id="A", center_lat=40.0, center_lon=29.0, size_km=5.0),
    ]
    records = scan_terrain(cells, client, use_cache=False)
    ranked = rank_by_flatness(records)
    assert ranked[0].cell_id == "A"

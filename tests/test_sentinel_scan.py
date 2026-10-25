from datetime import date
from pathlib import Path

from land_radar.grid import GridCell
from land_radar.providers.sentinel_surface import SurfaceSummary
from land_radar.sentinel_scan import scan_sentinel_change


class FakeSurfaceClient:
    def __init__(self):
        self.calls = 0

    def summary(
        self,
        bbox,
        start_date,
        end_date,
        *,
        width=128,
        height=128,
        max_cloud_coverage=30,
    ):
        self.calls += 1
        newer = start_date.year >= 2026
        return SurfaceSummary(
            start_date=start_date,
            end_date=end_date,
            median_ndvi=0.30 if newer else 0.40,
            median_ndbi=0.10 if newer else 0.05,
            median_bsi=0.08 if newer else 0.02,
            vegetation_share=0.40 if newer else 0.50,
            bare_soil_share=0.30 if newer else 0.20,
            water_share=0.05,
            valid_land_pixels=100,
            total_valid_pixels=120,
        )


def test_sentinel_change_scan_uses_cache(tmp_path: Path):
    cells = [
        GridCell(
            cell_id="A",
            center_lat=40.0,
            center_lon=29.0,
            size_km=5.0,
        )
    ]
    client = FakeSurfaceClient()

    kwargs = dict(
        first_start=date(2025, 8, 1),
        first_end=date(2025, 9, 30),
        second_start=date(2026, 8, 1),
        second_end=date(2026, 9, 30),
        cache_dir=tmp_path,
    )

    first = scan_sentinel_change(cells, client, **kwargs)
    second = scan_sentinel_change(cells, client, **kwargs)

    assert client.calls == 2
    assert first[0].cache_hit is False
    assert second[0].cache_hit is True
    assert first[0].delta_ndvi == -0.1
    assert first[0].delta_ndbi == 0.05
    assert first[0].delta_bare_soil_share_pp == 10.0

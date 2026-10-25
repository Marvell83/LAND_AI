from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from land_radar.grid import GridCell
from land_radar.urban_scan import rank_accelerating, scan_grid_ghsl


def _write_epoch(directory: Path, epoch: int, value: int) -> None:
    path = directory / f"GHS_BUILT_S_E{epoch}_TEST.tif"
    data = np.full((20, 20), value, dtype="uint16")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=20,
        width=20,
        count=1,
        dtype="uint16",
        crs="EPSG:4326",
        transform=from_origin(0.0, 0.2, 0.01, 0.01),
        nodata=65535,
    ) as dst:
        dst.write(data, 1)


def test_scan_grid_ghsl(tmp_path: Path):
    _write_epoch(tmp_path, 2010, 10)
    _write_epoch(tmp_path, 2015, 15)
    _write_epoch(tmp_path, 2020, 30)

    cells = [
        GridCell(cell_id="A", center_lat=0.10, center_lon=0.10, size_km=1.0),
    ]
    records = scan_grid_ghsl(cells, tmp_path)
    assert len(records) == 1
    assert records[0].signal == "accelerating"
    assert records[0].acceleration_pp_per_year is not None


def test_rank_accelerating_keeps_measurable_first(tmp_path: Path):
    _write_epoch(tmp_path, 2010, 10)
    _write_epoch(tmp_path, 2015, 15)
    _write_epoch(tmp_path, 2020, 30)

    cells = [
        GridCell(cell_id="A", center_lat=0.10, center_lon=0.10, size_km=1.0),
        GridCell(cell_id="B", center_lat=0.12, center_lon=0.12, size_km=1.0),
    ]
    ranked = rank_accelerating(scan_grid_ghsl(cells, tmp_path))
    assert {r.cell_id for r in ranked} == {"A", "B"}

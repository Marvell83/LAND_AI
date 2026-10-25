from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from land_radar.providers.ghsl import (
    compare_built_up,
    epoch_from_filename,
    summarize_built_up,
)


def _write_raster(path: Path, values: np.ndarray) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype=values.dtype,
        crs="EPSG:4326",
        transform=from_origin(0.0, 1.0, 0.25, 0.25),
        nodata=65535,
    ) as dst:
        dst.write(values, 1)


def test_epoch_from_filename():
    assert epoch_from_filename("GHS_BUILT_S_E2020_GLOBE_R2023A_54009_100_V1_0.tif") == 2020
    assert epoch_from_filename("other.tif") is None


def test_summarize_and_compare(tmp_path: Path):
    start_path = tmp_path / "GHS_BUILT_S_E2010_TEST.tif"
    end_path = tmp_path / "GHS_BUILT_S_E2015_TEST.tif"

    start = np.array(
        [
            [0, 0, 10, 10],
            [0, 10, 10, 10],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ],
        dtype="uint16",
    )
    end = np.array(
        [
            [0, 10, 20, 20],
            [10, 20, 20, 20],
            [0, 10, 10, 0],
            [0, 0, 0, 0],
        ],
        dtype="uint16",
    )

    _write_raster(start_path, start)
    _write_raster(end_path, end)

    bbox = (0.0, 0.0, 1.0, 1.0)
    s0 = summarize_built_up(start_path, bbox)
    s1 = summarize_built_up(end_path, bbox)
    change = compare_built_up(s0, s1)

    assert s0.epoch == 2010
    assert s1.epoch == 2015
    assert s0.total_built_up_m2 == 50.0
    assert s1.total_built_up_m2 == 140.0
    assert change.absolute_change_m2 == 90.0
    assert change.percent_change == 180.0
    assert change.occupied_share_change_pp > 0

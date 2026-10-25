from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

from land_radar.providers.ghsl import (
    GHSLRasterStack,
    compare_built_up,
    discover_epoch_files,
    epoch_from_filename,
    summarize_built_up,
)


def _write_raster(
    path: Path,
    values: np.ndarray,
    *,
    west: float = 0.0,
    north: float = 1.0,
    pixel_size: float = 0.25,
) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype=values.dtype,
        crs="EPSG:4326",
        transform=from_origin(west, north, pixel_size, pixel_size),
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


def test_multi_tile_epoch_combines_intersecting_tiles(tmp_path: Path):
    left_path = tmp_path / "A_GHS_BUILT_S_E2020_TEST.tif"
    right_path = tmp_path / "B_GHS_BUILT_S_E2020_TEST.tif"

    left = np.full((4, 4), 10, dtype="uint16")
    right = np.full((4, 4), 20, dtype="uint16")

    _write_raster(left_path, left, west=0.0, north=1.0)
    _write_raster(right_path, right, west=1.0, north=1.0)

    matches = discover_epoch_files(tmp_path, 2020)
    assert matches == (left_path, right_path)

    with GHSLRasterStack(tmp_path, epochs=(2020,)) as stack:
        summary = stack.summarize(
            2020,
            (0.5, 0.0, 1.5, 1.0),
        )

    # Half of each 1x1-degree tile is included: 8 pixels from each tile.
    assert summary.valid_pixels == 16
    assert summary.total_built_up_m2 == 8 * 10 + 8 * 20
    assert str(left_path) in summary.source_path
    assert str(right_path) in summary.source_path


def test_multi_tile_stack_ignores_non_intersecting_tile(tmp_path: Path):
    near_path = tmp_path / "A_GHS_BUILT_S_E2020_TEST.tif"
    far_path = tmp_path / "B_GHS_BUILT_S_E2020_TEST.tif"

    _write_raster(
        near_path,
        np.full((4, 4), 10, dtype="uint16"),
        west=0.0,
        north=1.0,
    )
    _write_raster(
        far_path,
        np.full((4, 4), 99, dtype="uint16"),
        west=10.0,
        north=11.0,
    )

    with GHSLRasterStack(tmp_path, epochs=(2020,)) as stack:
        summary = stack.summarize(
            2020,
            (0.0, 0.0, 1.0, 1.0),
        )

    assert summary.total_built_up_m2 == 16 * 10
    assert str(near_path) in summary.source_path
    assert str(far_path) not in summary.source_path

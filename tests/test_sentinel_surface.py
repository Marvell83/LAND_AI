from datetime import date

import numpy as np
import pytest

from land_radar.providers.sentinel_surface import (
    build_surface_process_payload,
    compare_surface,
    summarize_surface_arrays,
)


def test_surface_payload_uses_sentinel2_l2a():
    payload = build_surface_process_payload(
        (26.0, 39.0, 26.1, 39.1),
        date(2025, 1, 1),
        date(2025, 1, 31),
        max_cloud_coverage=20,
    )
    data = payload["input"]["data"][0]
    assert data["type"] == "sentinel-2-l2a"
    assert data["dataFilter"]["mosaickingOrder"] == "leastCC"
    assert data["dataFilter"]["maxCloudCoverage"] == 20


def test_surface_payload_rejects_bad_dates():
    with pytest.raises(ValueError):
        build_surface_process_payload(
            (26.0, 39.0, 26.1, 39.1),
            date(2025, 2, 1),
            date(2025, 1, 1),
        )


def test_surface_indices_and_change():
    blue = np.full((4, 4), 0.10)
    red = np.full((4, 4), 0.20)
    nir = np.full((4, 4), 0.40)
    swir = np.full((4, 4), 0.30)
    scl = np.full((4, 4), 4.0)
    mask = np.ones((4, 4))

    first = summarize_surface_arrays(
        blue, red, nir, swir, scl, mask,
        date(2024, 6, 1), date(2024, 6, 30),
    )

    red2 = np.full((4, 4), 0.25)
    nir2 = np.full((4, 4), 0.30)
    swir2 = np.full((4, 4), 0.40)
    scl2 = np.full((4, 4), 5.0)
    second = summarize_surface_arrays(
        blue, red2, nir2, swir2, scl2, mask,
        date(2025, 6, 1), date(2025, 6, 30),
    )

    change = compare_surface(first, second)

    assert first.vegetation_share == 1.0
    assert second.bare_soil_share == 1.0
    assert change.delta_ndvi is not None
    assert change.delta_ndbi is not None
    assert change.delta_ndvi < 0
    assert change.delta_ndbi > 0
    assert change.delta_vegetation_share_pp == -100.0
    assert change.delta_bare_soil_share_pp == 100.0

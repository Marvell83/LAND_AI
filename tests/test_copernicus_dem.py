import numpy as np
import pytest

from land_radar.providers.copernicus_dem import (
    build_dem_process_payload,
    summarize_dem_array,
)


def test_dem_payload_uses_public_90m_by_default():
    payload = build_dem_process_payload((26.0, 39.0, 26.1, 39.1))
    data = payload["input"]["data"][0]
    assert data["type"] == "dem"
    assert data["dataFilter"]["demInstance"] == "COPERNICUS_90"
    assert payload["output"]["responses"][0]["format"]["type"] == "image/tiff"


def test_dem_payload_rejects_unknown_instance():
    with pytest.raises(ValueError):
        build_dem_process_payload(
            (26.0, 39.0, 26.1, 39.1),
            dem_instance="UNKNOWN",
        )


def test_flat_dem_has_zero_slope():
    elevation = np.full((10, 10), 100.0, dtype="float64")
    mask = np.ones((10, 10), dtype="uint8")
    summary = summarize_dem_array(
        elevation,
        mask,
        (26.0, 39.0, 26.1, 39.1),
    )
    assert summary.mean_elevation_m == 100.0
    assert summary.mean_slope_deg == 0.0
    assert summary.p90_slope_deg == 0.0


def test_gradient_dem_has_positive_slope():
    x = np.linspace(0.0, 100.0, 20)
    elevation = np.tile(x, (20, 1))
    mask = np.ones((20, 20), dtype="uint8")
    summary = summarize_dem_array(
        elevation,
        mask,
        (26.0, 39.0, 26.02, 39.02),
    )
    assert summary.mean_slope_deg > 0
    assert summary.max_slope_deg > 0

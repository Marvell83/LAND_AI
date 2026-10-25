from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
from rasterio.io import MemoryFile
import requests

from .cdse_oauth import CDSEAuthError, CDSEProcessError, CDSEProcessSession


class SentinelSurfaceError(RuntimeError):
    pass


@dataclass(frozen=True)
class SurfaceSummary:
    start_date: date
    end_date: date
    median_ndvi: float | None
    median_ndbi: float | None
    median_bsi: float | None
    vegetation_share: float
    bare_soil_share: float
    water_share: float
    valid_land_pixels: int
    total_valid_pixels: int


@dataclass(frozen=True)
class SurfaceChange:
    first: SurfaceSummary
    second: SurfaceSummary
    delta_ndvi: float | None
    delta_ndbi: float | None
    delta_bsi: float | None
    delta_vegetation_share_pp: float
    delta_bare_soil_share_pp: float
    delta_water_share_pp: float


EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: ["B02", "B04", "B08", "B11", "SCL", "dataMask"],
    output: {
      bands: 6,
      sampleType: SampleType.FLOAT32
    }
  };
}
function evaluatePixel(sample) {
  return [
    sample.B02,
    sample.B04,
    sample.B08,
    sample.B11,
    sample.SCL,
    sample.dataMask
  ];
}
"""


def _start_iso(value: date) -> str:
    return value.isoformat() + "T00:00:00Z"


def _end_iso(value: date) -> str:
    return value.isoformat() + "T23:59:59Z"


def build_surface_process_payload(
    bbox: tuple[float, float, float, float],
    start_date: date,
    end_date: date,
    *,
    width: int = 128,
    height: int = 128,
    max_cloud_coverage: int = 30,
) -> dict[str, Any]:
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")
    if not 0 <= max_cloud_coverage <= 100:
        raise ValueError("max_cloud_coverage must be between 0 and 100")
    if width < 16 or height < 16:
        raise ValueError("Sentinel output dimensions must be at least 16x16")
    if width > 1024 or height > 1024:
        raise ValueError("Sentinel output dimensions are capped at 1024")

    return {
        "input": {
            "bounds": {
                "bbox": list(bbox),
                "properties": {
                    "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
                },
            },
            "data": [
                {
                    "type": "sentinel-2-l2a",
                    "dataFilter": {
                        "timeRange": {
                            "from": _start_iso(start_date),
                            "to": _end_iso(end_date),
                        },
                        "maxCloudCoverage": int(max_cloud_coverage),
                        "mosaickingOrder": "leastCC",
                    },
                    "processing": {
                        "upsampling": "BILINEAR",
                        "downsampling": "BILINEAR",
                    },
                }
            ],
        },
        "output": {
            "width": int(width),
            "height": int(height),
            "responses": [
                {
                    "identifier": "default",
                    "format": {"type": "image/tiff"},
                }
            ],
        },
        "evalscript": EVALSCRIPT,
    }


def _safe_index(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    denom = a + b
    result = np.full_like(denom, np.nan, dtype="float64")
    mask = np.abs(denom) > 1e-9
    result[mask] = (a[mask] - b[mask]) / denom[mask]
    return result


def summarize_surface_arrays(
    blue: np.ndarray,
    red: np.ndarray,
    nir: np.ndarray,
    swir: np.ndarray,
    scl: np.ndarray,
    data_mask: np.ndarray,
    start_date: date,
    end_date: date,
) -> SurfaceSummary:
    arrays = [blue, red, nir, swir, scl, data_mask]
    if any(arr.ndim != 2 for arr in arrays):
        raise ValueError("Sentinel arrays must be two-dimensional")
    shapes = {arr.shape for arr in arrays}
    if len(shapes) != 1:
        raise ValueError("All Sentinel arrays must have the same shape")

    valid = (data_mask > 0) & np.isfinite(blue) & np.isfinite(red) & np.isfinite(nir) & np.isfinite(swir)
    if not np.any(valid):
        raise SentinelSurfaceError("Sentinel response contains no valid pixels")

    scl_i = np.rint(scl).astype("int16")
    vegetation = valid & (scl_i == 4)
    bare = valid & (scl_i == 5)
    water = valid & (scl_i == 6)

    # Keep only land classes that are reasonably interpretable for spectral indices.
    # SCL 2 = dark-area pixels, 4 = vegetation, 5 = bare soils.
    land = valid & np.isin(scl_i, [2, 4, 5])

    total_valid = int(np.count_nonzero(valid))
    land_count = int(np.count_nonzero(land))

    ndvi = _safe_index(nir.astype("float64"), red.astype("float64"))
    ndbi = _safe_index(swir.astype("float64"), nir.astype("float64"))

    bsi_num_a = swir.astype("float64") + red.astype("float64")
    bsi_num_b = nir.astype("float64") + blue.astype("float64")
    bsi = _safe_index(bsi_num_a, bsi_num_b)

    def median_on_land(values: np.ndarray) -> float | None:
        if land_count == 0:
            return None
        selected = values[land]
        selected = selected[np.isfinite(selected)]
        if selected.size == 0:
            return None
        return round(float(np.median(selected)), 5)

    return SurfaceSummary(
        start_date=start_date,
        end_date=end_date,
        median_ndvi=median_on_land(ndvi),
        median_ndbi=median_on_land(ndbi),
        median_bsi=median_on_land(bsi),
        vegetation_share=round(float(np.count_nonzero(vegetation) / total_valid), 6),
        bare_soil_share=round(float(np.count_nonzero(bare) / total_valid), 6),
        water_share=round(float(np.count_nonzero(water) / total_valid), 6),
        valid_land_pixels=land_count,
        total_valid_pixels=total_valid,
    )


def parse_surface_tiff(
    content: bytes,
    start_date: date,
    end_date: date,
) -> SurfaceSummary:
    try:
        with MemoryFile(content) as memfile:
            with memfile.open() as dataset:
                if dataset.count < 6:
                    raise SentinelSurfaceError(
                        "Sentinel TIFF response does not contain the expected six bands"
                    )
                bands = [dataset.read(i).astype("float64") for i in range(1, 7)]
    except SentinelSurfaceError:
        raise
    except Exception as exc:
        raise SentinelSurfaceError(f"Failed to parse Sentinel TIFF: {exc}") from exc

    return summarize_surface_arrays(*bands, start_date, end_date)


def compare_surface(first: SurfaceSummary, second: SurfaceSummary) -> SurfaceChange:
    def delta(a: float | None, b: float | None) -> float | None:
        if a is None or b is None:
            return None
        return round(b - a, 5)

    return SurfaceChange(
        first=first,
        second=second,
        delta_ndvi=delta(first.median_ndvi, second.median_ndvi),
        delta_ndbi=delta(first.median_ndbi, second.median_ndbi),
        delta_bsi=delta(first.median_bsi, second.median_bsi),
        delta_vegetation_share_pp=round(
            (second.vegetation_share - first.vegetation_share) * 100.0,
            3,
        ),
        delta_bare_soil_share_pp=round(
            (second.bare_soil_share - first.bare_soil_share) * 100.0,
            3,
        ),
        delta_water_share_pp=round(
            (second.water_share - first.water_share) * 100.0,
            3,
        ),
    )


class SentinelSurfaceClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        session: requests.Session | None = None,
    ):
        self.process_session = CDSEProcessSession(
            client_id,
            client_secret,
            session=session,
        )

    def summary(
        self,
        bbox: tuple[float, float, float, float],
        start_date: date,
        end_date: date,
        *,
        width: int = 128,
        height: int = 128,
        max_cloud_coverage: int = 30,
    ) -> SurfaceSummary:
        payload = build_surface_process_payload(
            bbox,
            start_date,
            end_date,
            width=width,
            height=height,
            max_cloud_coverage=max_cloud_coverage,
        )
        try:
            content = self.process_session.process(payload, accept="image/tiff", timeout=90)
        except (CDSEAuthError, CDSEProcessError) as exc:
            raise SentinelSurfaceError(str(exc)) from exc

        return parse_surface_tiff(content, start_date, end_date)

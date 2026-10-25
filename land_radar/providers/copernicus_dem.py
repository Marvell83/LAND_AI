from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

import numpy as np
from rasterio.io import MemoryFile
import requests

from .cdse_oauth import CDSEAuthError, CDSEProcessError, CDSEProcessSession


DEFAULT_DEM_INSTANCE = "COPERNICUS_90"


class CopernicusDEMError(RuntimeError):
    pass


@dataclass(frozen=True)
class TerrainSummary:
    mean_elevation_m: float
    min_elevation_m: float
    max_elevation_m: float
    mean_slope_deg: float
    p90_slope_deg: float
    max_slope_deg: float
    valid_pixels: int
    dem_instance: str


EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: ["DEM", "dataMask"],
    output: {
      bands: 2,
      sampleType: SampleType.FLOAT32
    }
  };
}
function evaluatePixel(sample) {
  return [sample.DEM, sample.dataMask];
}
"""


def build_dem_process_payload(
    bbox: tuple[float, float, float, float],
    *,
    width: int = 96,
    height: int = 96,
    dem_instance: str = DEFAULT_DEM_INSTANCE,
) -> dict[str, Any]:
    if width < 8 or height < 8:
        raise ValueError("DEM output dimensions must be at least 8x8")
    if width > 1024 or height > 1024:
        raise ValueError("DEM output dimensions are capped at 1024")
    if dem_instance not in {"COPERNICUS_90", "COPERNICUS_30"}:
        raise ValueError("Unsupported dem_instance")

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
                    "type": "dem",
                    "dataFilter": {"demInstance": dem_instance},
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


def _bbox_dimensions_m(
    bbox: tuple[float, float, float, float],
) -> tuple[float, float]:
    min_lon, min_lat, max_lon, max_lat = bbox
    mean_lat = (min_lat + max_lat) / 2.0
    height_m = abs(max_lat - min_lat) * 111_320.0
    width_m = abs(max_lon - min_lon) * 111_320.0 * max(
        0.01, math.cos(math.radians(mean_lat))
    )
    return width_m, height_m


def summarize_dem_array(
    elevation: np.ndarray,
    data_mask: np.ndarray,
    bbox: tuple[float, float, float, float],
    *,
    dem_instance: str = DEFAULT_DEM_INSTANCE,
) -> TerrainSummary:
    if elevation.ndim != 2 or data_mask.ndim != 2:
        raise ValueError("DEM arrays must be two-dimensional")
    if elevation.shape != data_mask.shape:
        raise ValueError("Elevation and data mask shapes must match")

    valid = (data_mask > 0) & np.isfinite(elevation)
    if not np.any(valid):
        raise CopernicusDEMError("DEM response contains no valid pixels")

    rows, cols = elevation.shape
    width_m, height_m = _bbox_dimensions_m(bbox)
    dx = width_m / max(1, cols - 1)
    dy = height_m / max(1, rows - 1)

    filled = np.array(elevation, dtype="float64", copy=True)
    if not np.all(valid):
        replacement = float(np.nanmedian(filled[valid]))
        filled[~valid] = replacement

    grad_y, grad_x = np.gradient(filled, dy, dx)
    slope_deg = np.degrees(np.arctan(np.hypot(grad_x, grad_y)))

    elev_valid = filled[valid]
    slope_valid = slope_deg[valid]

    return TerrainSummary(
        mean_elevation_m=round(float(np.mean(elev_valid)), 2),
        min_elevation_m=round(float(np.min(elev_valid)), 2),
        max_elevation_m=round(float(np.max(elev_valid)), 2),
        mean_slope_deg=round(float(np.mean(slope_valid)), 3),
        p90_slope_deg=round(float(np.percentile(slope_valid, 90)), 3),
        max_slope_deg=round(float(np.max(slope_valid)), 3),
        valid_pixels=int(np.count_nonzero(valid)),
        dem_instance=dem_instance,
    )


def parse_dem_tiff(
    content: bytes,
    bbox: tuple[float, float, float, float],
    *,
    dem_instance: str = DEFAULT_DEM_INSTANCE,
) -> TerrainSummary:
    try:
        with MemoryFile(content) as memfile:
            with memfile.open() as dataset:
                if dataset.count < 2:
                    raise CopernicusDEMError("DEM TIFF response is missing dataMask band")
                elevation = dataset.read(1).astype("float64")
                data_mask = dataset.read(2)
    except CopernicusDEMError:
        raise
    except Exception as exc:
        raise CopernicusDEMError(f"Failed to parse DEM TIFF: {exc}") from exc

    return summarize_dem_array(
        elevation,
        data_mask,
        bbox,
        dem_instance=dem_instance,
    )


class CopernicusProcessClient:
    """Backward-compatible DEM client using the shared CDSE OAuth session."""

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

    def terrain_summary(
        self,
        bbox: tuple[float, float, float, float],
        *,
        width: int = 96,
        height: int = 96,
        dem_instance: str = DEFAULT_DEM_INSTANCE,
    ) -> TerrainSummary:
        payload = build_dem_process_payload(
            bbox,
            width=width,
            height=height,
            dem_instance=dem_instance,
        )
        try:
            content = self.process_session.process(payload, accept="image/tiff", timeout=60)
        except (CDSEAuthError, CDSEProcessError) as exc:
            raise CopernicusDEMError(str(exc)) from exc

        return parse_dem_tiff(
            content,
            bbox,
            dem_instance=dem_instance,
        )

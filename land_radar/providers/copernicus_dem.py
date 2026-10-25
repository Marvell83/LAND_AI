from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import math
import time
from typing import Any

import numpy as np
import rasterio
from rasterio.io import MemoryFile
import requests


TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/process/v1"
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
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        *,
        session: requests.Session | None = None,
    ):
        if not client_id or not client_secret:
            raise ValueError("Copernicus client_id and client_secret are required")
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = session or requests.Session()
        self._access_token: str | None = None
        self._expires_at: float = 0.0

    def _token(self) -> str:
        if self._access_token and time.time() < self._expires_at - 60:
            return self._access_token

        try:
            response = self.session.post(
                TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
            token = payload.get("access_token")
            if not token:
                raise CopernicusDEMError("OAuth response did not contain access_token")
            expires_in = float(payload.get("expires_in", 3600))
        except (requests.RequestException, ValueError) as exc:
            raise CopernicusDEMError(f"Copernicus OAuth failed: {exc}") from exc

        self._access_token = str(token)
        self._expires_at = time.time() + max(60.0, expires_in)
        return self._access_token

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
        token = self._token()

        try:
            response = self.session.post(
                PROCESS_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "image/tiff",
                    "Content-Type": "application/json",
                },
                timeout=60,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise CopernicusDEMError(f"Copernicus DEM Process API failed: {exc}") from exc

        return parse_dem_tiff(
            response.content,
            bbox,
            dem_instance=dem_instance,
        )

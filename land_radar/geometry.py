from __future__ import annotations

import math

from .grid import GridCell


def bbox_for_cell(cell: GridCell, padding_km: float = 0.0) -> tuple[float, float, float, float]:
    """Return (min_lon, min_lat, max_lon, max_lat) for an approximate square cell."""
    if padding_km < 0:
        raise ValueError("padding_km cannot be negative")

    half_km = cell.size_km / 2.0 + padding_km
    lat_delta = half_km / 111.32
    lon_km_per_degree = 111.32 * max(0.1, math.cos(math.radians(cell.center_lat)))
    lon_delta = half_km / lon_km_per_degree

    return (
        cell.center_lon - lon_delta,
        cell.center_lat - lat_delta,
        cell.center_lon + lon_delta,
        cell.center_lat + lat_delta,
    )

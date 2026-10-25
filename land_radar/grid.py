from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class GridCell:
    cell_id: str
    center_lat: float
    center_lon: float
    size_km: float


def generate_rectangular_grid(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    cell_km: float = 5.0,
) -> list[GridCell]:
    """Generate an approximate WGS84 rectangular research grid.

    This is deliberately simple for the V0 pilot. It is not a cadastral
    geometry engine and must not be used for parcel boundaries.
    """
    if cell_km <= 0:
        raise ValueError("cell_km must be positive")
    if min_lat >= max_lat or min_lon >= max_lon:
        raise ValueError("invalid bounding box")

    mean_lat = (min_lat + max_lat) / 2.0
    lat_step = cell_km / 111.32
    lon_km_per_degree = 111.32 * max(0.1, math.cos(math.radians(mean_lat)))
    lon_step = cell_km / lon_km_per_degree

    cells: list[GridCell] = []
    row = 0
    lat = min_lat + lat_step / 2
    while lat < max_lat:
        col = 0
        lon = min_lon + lon_step / 2
        while lon < max_lon:
            cells.append(
                GridCell(
                    cell_id=f"LR-{row:03d}-{col:03d}",
                    center_lat=round(lat, 6),
                    center_lon=round(lon, 6),
                    size_km=cell_km,
                )
            )
            col += 1
            lon += lon_step
        row += 1
        lat += lat_step

    return cells

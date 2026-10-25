from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pyproj import CRS, Transformer
from shapely.geometry import Point, box
from shapely.ops import transform

from ..geometry import bbox_for_cell
from ..grid import GridCell
from .geometry import GeometryEvidence, geometry_from_geojson


@dataclass(frozen=True)
class SpatialDistance:
    distance_km: float
    intersects_cell: bool
    projection: str


def _local_aeqd_crs(lat: float, lon: float) -> CRS:
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat} +lon_0={lon} "
        "+datum=WGS84 +units=m +no_defs"
    )


def _projected_geometries(
    cell: GridCell,
    geometry_geojson: dict[str, Any],
):
    min_lon, min_lat, max_lon, max_lat = bbox_for_cell(cell)
    cell_wgs84 = box(min_lon, min_lat, max_lon, max_lat)
    target_wgs84 = geometry_from_geojson(geometry_geojson)

    local_crs = _local_aeqd_crs(cell.center_lat, cell.center_lon)
    transformer = Transformer.from_crs("EPSG:4326", local_crs, always_xy=True)
    project = transformer.transform

    return (
        transform(project, cell_wgs84),
        transform(project, target_wgs84),
        local_crs,
    )


def distance_from_cell_to_geometry(
    cell: GridCell,
    geometry: GeometryEvidence | dict[str, Any],
) -> SpatialDistance:
    """Minimum edge-to-geometry distance for a research cell.

    If the geometry intersects the square research cell, distance is 0.
    Distances are computed in a local azimuthal-equidistant CRS centered on the
    cell, avoiding degree-distance mistakes.
    """
    geometry_geojson = (
        geometry.geometry_geojson
        if isinstance(geometry, GeometryEvidence)
        else geometry
    )
    cell_metric, target_metric, crs = _projected_geometries(
        cell,
        geometry_geojson,
    )
    intersects = cell_metric.intersects(target_metric)
    distance_m = 0.0 if intersects else float(cell_metric.distance(target_metric))

    return SpatialDistance(
        distance_km=round(distance_m / 1000.0, 4),
        intersects_cell=intersects,
        projection=crs.to_string(),
    )


def distance_from_point_to_geometry(
    lat: float,
    lon: float,
    geometry: GeometryEvidence | dict[str, Any],
) -> float:
    geometry_geojson = (
        geometry.geometry_geojson
        if isinstance(geometry, GeometryEvidence)
        else geometry
    )
    target_wgs84 = geometry_from_geojson(geometry_geojson)

    local_crs = _local_aeqd_crs(lat, lon)
    transformer = Transformer.from_crs("EPSG:4326", local_crs, always_xy=True)
    project = transformer.transform

    point_metric = transform(project, Point(lon, lat))
    target_metric = transform(project, target_wgs84)
    return round(float(point_metric.distance(target_metric)) / 1000.0, 4)

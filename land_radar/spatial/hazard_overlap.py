from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from pyproj import CRS, Transformer
from shapely.geometry import box
from shapely.ops import transform

from ..geometry import bbox_for_cell
from ..grid import GridCell
from ..hazard import HazardGeometry, HazardSeverity
from .geometry import geometry_from_geojson


@dataclass(frozen=True)
class HazardCellLink:
    cell_id: str
    hazard_id: str
    category: str
    severity: HazardSeverity
    hard_veto: bool
    source: str
    confidence: float
    intersects_cell: bool
    overlap_ratio: float
    distance_km: float


@dataclass(frozen=True)
class CellHazardSummary:
    cell_id: str
    finding_count: int
    hard_veto: bool
    hard_veto_categories: tuple[str, ...]
    max_severity: HazardSeverity
    max_overlap_ratio: float
    nearest_hazard_km: float | None


def _local_crs(cell: GridCell) -> CRS:
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={cell.center_lat} +lon_0={cell.center_lon} "
        "+datum=WGS84 +units=m +no_defs"
    )


def link_hazard_to_cell(
    cell: GridCell,
    hazard: HazardGeometry,
) -> HazardCellLink:
    min_lon, min_lat, max_lon, max_lat = bbox_for_cell(cell)
    cell_wgs = box(min_lon, min_lat, max_lon, max_lat)
    hazard_wgs = geometry_from_geojson(hazard.geometry_geojson)

    transformer = Transformer.from_crs(
        "EPSG:4326",
        _local_crs(cell),
        always_xy=True,
    )
    project = transformer.transform
    cell_metric = transform(project, cell_wgs)
    hazard_metric = transform(project, hazard_wgs)

    intersects = cell_metric.intersects(hazard_metric)
    distance_m = 0.0 if intersects else float(cell_metric.distance(hazard_metric))

    overlap_ratio = 0.0
    if intersects and cell_metric.area > 0:
        intersection = cell_metric.intersection(hazard_metric)
        overlap_ratio = float(intersection.area / cell_metric.area)

    return HazardCellLink(
        cell_id=cell.cell_id,
        hazard_id=hazard.hazard_id,
        category=hazard.category,
        severity=hazard.severity,
        hard_veto=hazard.hard_veto,
        source=hazard.source,
        confidence=float(hazard.confidence),
        intersects_cell=intersects,
        overlap_ratio=round(overlap_ratio, 6),
        distance_km=round(distance_m / 1000.0, 4),
    )


def batch_link_hazards(
    cells: Iterable[GridCell],
    hazards: Iterable[HazardGeometry],
    *,
    max_distance_km: float | None = 20.0,
) -> list[HazardCellLink]:
    if max_distance_km is not None and max_distance_km < 0:
        raise ValueError("max_distance_km cannot be negative")

    hazard_list = list(hazards)
    links: list[HazardCellLink] = []
    for cell in cells:
        for hazard in hazard_list:
            link = link_hazard_to_cell(cell, hazard)
            if (
                max_distance_km is None
                or link.distance_km <= max_distance_km
            ):
                links.append(link)

    links.sort(
        key=lambda link: (
            link.cell_id,
            link.distance_km,
            -int(link.severity),
            link.hazard_id,
        )
    )
    return links


def summarize_cell_hazards(
    cell_id: str,
    links: Iterable[HazardCellLink],
) -> CellHazardSummary:
    items = [link for link in links if link.cell_id == cell_id]
    if not items:
        return CellHazardSummary(
            cell_id=cell_id,
            finding_count=0,
            hard_veto=False,
            hard_veto_categories=tuple(),
            max_severity=HazardSeverity.NONE,
            max_overlap_ratio=0.0,
            nearest_hazard_km=None,
        )

    veto_categories = tuple(sorted({
        link.category
        for link in items
        if link.hard_veto and link.intersects_cell
    }))

    return CellHazardSummary(
        cell_id=cell_id,
        finding_count=len(items),
        hard_veto=bool(veto_categories),
        hard_veto_categories=veto_categories,
        max_severity=max(link.severity for link in items),
        max_overlap_ratio=round(max(link.overlap_ratio for link in items), 6),
        nearest_hazard_km=min(link.distance_km for link in items),
    )

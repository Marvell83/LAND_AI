from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from pyproj import CRS, Transformer
from shapely.geometry import box
from shapely.ops import transform

from ..geometry import bbox_for_cell
from ..grid import GridCell
from ..planning import LegalEffect, PlanningConstraint
from .geometry import geometry_from_geojson


@dataclass(frozen=True)
class PlanningCellLink:
    cell_id: str
    constraint_id: str
    category: str
    legal_effect: LegalEffect
    hard_veto: bool
    source: str
    confidence: float
    intersects_cell: bool
    overlap_ratio: float
    distance_km: float


@dataclass(frozen=True)
class CellPlanningSummary:
    cell_id: str
    checked: bool
    finding_count: int
    intersecting_count: int
    legal_review_required: bool
    hard_veto: bool
    hard_veto_categories: tuple[str, ...]
    max_legal_effect: LegalEffect
    max_overlap_ratio: float
    nearest_constraint_km: float | None


def _local_crs(cell: GridCell) -> CRS:
    return CRS.from_proj4(
        f"+proj=aeqd +lat_0={cell.center_lat} +lon_0={cell.center_lon} "
        "+datum=WGS84 +units=m +no_defs"
    )


def link_constraint_to_cell(
    cell: GridCell,
    constraint: PlanningConstraint,
) -> PlanningCellLink:
    min_lon, min_lat, max_lon, max_lat = bbox_for_cell(cell)
    cell_wgs = box(min_lon, min_lat, max_lon, max_lat)
    constraint_wgs = geometry_from_geojson(constraint.geometry_geojson)

    transformer = Transformer.from_crs(
        "EPSG:4326",
        _local_crs(cell),
        always_xy=True,
    )
    project = transformer.transform
    cell_metric = transform(project, cell_wgs)
    constraint_metric = transform(project, constraint_wgs)

    intersects = cell_metric.intersects(constraint_metric)
    distance_m = 0.0 if intersects else float(
        cell_metric.distance(constraint_metric)
    )

    overlap_ratio = 0.0
    if intersects and cell_metric.area > 0:
        overlap_ratio = float(
            cell_metric.intersection(constraint_metric).area
            / cell_metric.area
        )

    return PlanningCellLink(
        cell_id=cell.cell_id,
        constraint_id=constraint.constraint_id,
        category=constraint.category,
        legal_effect=constraint.legal_effect,
        hard_veto=constraint.hard_veto,
        source=constraint.source,
        confidence=float(constraint.confidence),
        intersects_cell=intersects,
        overlap_ratio=round(overlap_ratio, 6),
        distance_km=round(distance_m / 1000.0, 4),
    )


def batch_link_constraints(
    cells: Iterable[GridCell],
    constraints: Iterable[PlanningConstraint],
    *,
    max_distance_km: float | None = 20.0,
) -> list[PlanningCellLink]:
    if max_distance_km is not None and max_distance_km < 0:
        raise ValueError("max_distance_km cannot be negative")

    constraint_list = list(constraints)
    links: list[PlanningCellLink] = []
    for cell in cells:
        for constraint in constraint_list:
            link = link_constraint_to_cell(cell, constraint)
            if max_distance_km is None or link.distance_km <= max_distance_km:
                links.append(link)

    links.sort(
        key=lambda link: (
            link.cell_id,
            link.distance_km,
            -int(link.legal_effect),
            link.constraint_id,
        )
    )
    return links


def summarize_cell_planning(
    cell_id: str,
    links: Iterable[PlanningCellLink],
    *,
    checked: bool,
) -> CellPlanningSummary:
    items = [link for link in links if link.cell_id == cell_id]

    if not items:
        return CellPlanningSummary(
            cell_id=cell_id,
            checked=checked,
            finding_count=0,
            intersecting_count=0,
            legal_review_required=False,
            hard_veto=False,
            hard_veto_categories=tuple(),
            max_legal_effect=LegalEffect.CONTEXT,
            max_overlap_ratio=0.0,
            nearest_constraint_km=None,
        )

    intersecting = [link for link in items if link.intersects_cell]
    veto_categories = tuple(sorted({
        link.category
        for link in intersecting
        if link.hard_veto
    }))

    return CellPlanningSummary(
        cell_id=cell_id,
        checked=checked,
        finding_count=len(items),
        intersecting_count=len(intersecting),
        legal_review_required=any(
            link.intersects_cell
            and link.legal_effect >= LegalEffect.REVIEW_REQUIRED
            for link in items
        ),
        hard_veto=bool(veto_categories),
        hard_veto_categories=veto_categories,
        max_legal_effect=max(link.legal_effect for link in items),
        max_overlap_ratio=round(
            max(link.overlap_ratio for link in items),
            6,
        ),
        nearest_constraint_km=min(link.distance_km for link in items),
    )

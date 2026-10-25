from __future__ import annotations

from dataclasses import dataclass

from ..catalyst import Catalyst
from ..grid import GridCell
from .distance import distance_from_cell_to_geometry
from .geometry import GeometryEvidence
from .influence import (
    DEFAULT_CONTEXT_PROFILE,
    InfluenceProfile,
    classify_influence,
)


@dataclass(frozen=True)
class CatalystSpatialLink:
    cell_id: str
    catalyst_id: str
    catalyst_name: str
    catalyst_category: str
    catalyst_stage: int
    status_evidence_confidence: float | None
    geometry_source: str
    geometry_confidence: float
    distance_km: float
    intersects_cell: bool
    influence_code: str
    influence_label: str
    evidence_complete: bool


def link_catalyst_to_cell(
    catalyst: Catalyst,
    geometry: GeometryEvidence,
    cell: GridCell,
    *,
    profile: InfluenceProfile = DEFAULT_CONTEXT_PROFILE,
) -> CatalystSpatialLink:
    catalyst.validate()

    distance = distance_from_cell_to_geometry(cell, geometry)
    influence = classify_influence(
        distance.distance_km,
        intersects_cell=distance.intersects_cell,
        profile=profile,
    )

    return CatalystSpatialLink(
        cell_id=cell.cell_id,
        catalyst_id=catalyst.catalyst_id,
        catalyst_name=catalyst.name,
        catalyst_category=catalyst.category,
        catalyst_stage=int(catalyst.stage),
        status_evidence_confidence=catalyst.evidence_confidence,
        geometry_source=geometry.source,
        geometry_confidence=float(geometry.confidence),
        distance_km=distance.distance_km,
        intersects_cell=distance.intersects_cell,
        influence_code=influence.code,
        influence_label=influence.label,
        evidence_complete=bool(catalyst.evidence and geometry.source),
    )

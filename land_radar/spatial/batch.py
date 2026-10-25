from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from ..catalyst import Catalyst
from ..grid import GridCell
from .catalyst_geometry import CatalystSpatialLink, link_catalyst_to_cell
from .registry import GeometryRegistryEntry


@dataclass(frozen=True)
class BatchSpatialResult:
    links: tuple[CatalystSpatialLink, ...]
    missing_catalysts: tuple[str, ...]
    missing_geometries: tuple[str, ...]


def batch_link_catalysts(
    cells: Iterable[GridCell],
    catalysts: Mapping[str, Catalyst],
    registry_entries: Iterable[GeometryRegistryEntry],
    *,
    max_distance_km: float | None = None,
) -> BatchSpatialResult:
    if max_distance_km is not None and max_distance_km < 0:
        raise ValueError("max_distance_km cannot be negative")

    entries = list(registry_entries)
    entries_by_catalyst: dict[str, list[GeometryRegistryEntry]] = {}
    for entry in entries:
        entries_by_catalyst.setdefault(entry.catalyst_id, []).append(entry)

    missing_catalysts = sorted(
        {
            entry.catalyst_id
            for entry in entries
            if entry.catalyst_id not in catalysts
        }
    )
    missing_geometries = sorted(
        catalyst_id
        for catalyst_id in catalysts
        if catalyst_id not in entries_by_catalyst
    )

    links: list[CatalystSpatialLink] = []
    for cell in cells:
        for catalyst_id, catalyst in catalysts.items():
            for entry in entries_by_catalyst.get(catalyst_id, []):
                link = link_catalyst_to_cell(
                    catalyst,
                    entry.evidence,
                    cell,
                )
                if (
                    max_distance_km is None
                    or link.distance_km <= max_distance_km
                ):
                    links.append(link)

    links.sort(
        key=lambda item: (
            item.cell_id,
            item.distance_km,
            item.catalyst_id,
        )
    )

    return BatchSpatialResult(
        links=tuple(links),
        missing_catalysts=tuple(missing_catalysts),
        missing_geometries=tuple(missing_geometries),
    )

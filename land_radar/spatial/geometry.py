from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry


class GeometryEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class GeometryEvidence:
    """A geometry observation with its own provenance.

    Geometry evidence is intentionally separate from catalyst/status evidence.
    An OSB can have an official status from OSBÜK while its current boundary is
    approximated from OpenStreetMap. Those must not be collapsed into one
    undifferentiated confidence value.
    """

    source: str
    feature_name: str
    geometry_geojson: dict[str, Any]
    observed_date: date | None = None
    source_url: str | None = None
    feature_id: str | None = None
    confidence: float = 50.0
    geometry_role: str = "observed_geometry"

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise GeometryEvidenceError("Geometry source cannot be empty")
        if not self.feature_name.strip():
            raise GeometryEvidenceError("Geometry feature_name cannot be empty")
        if not 0 <= float(self.confidence) <= 100:
            raise GeometryEvidenceError("Geometry confidence must be between 0 and 100")
        geometry = geometry_from_geojson(self.geometry_geojson)
        if geometry.is_empty:
            raise GeometryEvidenceError("Geometry cannot be empty")


def geometry_from_geojson(value: dict[str, Any]) -> BaseGeometry:
    try:
        geometry = shape(value)
    except Exception as exc:
        raise GeometryEvidenceError(f"Invalid GeoJSON geometry: {exc}") from exc

    if geometry.is_empty:
        raise GeometryEvidenceError("Geometry cannot be empty")
    if not geometry.is_valid:
        # buffer(0) is a standard conservative repair for simple polygon issues.
        repaired = geometry.buffer(0)
        if repaired.is_empty or not repaired.is_valid:
            raise GeometryEvidenceError("Geometry is invalid and could not be repaired")
        geometry = repaired
    return geometry

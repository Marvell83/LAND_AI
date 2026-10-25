from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

from .geometry import GeometryEvidence


@dataclass(frozen=True)
class GeometryRegistryEntry:
    catalyst_id: str
    evidence: GeometryEvidence
    manual_verified: bool = False

    def __post_init__(self) -> None:
        if not self.catalyst_id.strip():
            raise ValueError("catalyst_id cannot be empty")


def entry_to_feature(entry: GeometryRegistryEntry) -> dict[str, Any]:
    ev = entry.evidence
    return {
        "type": "Feature",
        "geometry": ev.geometry_geojson,
        "properties": {
            "catalyst_id": entry.catalyst_id,
            "source": ev.source,
            "feature_name": ev.feature_name,
            "observed_date": (
                ev.observed_date.isoformat()
                if ev.observed_date is not None
                else None
            ),
            "source_url": ev.source_url,
            "feature_id": ev.feature_id,
            "confidence": ev.confidence,
            "geometry_role": ev.geometry_role,
            "manual_verified": entry.manual_verified,
        },
    }


def feature_to_entry(feature: dict[str, Any]) -> GeometryRegistryEntry:
    if feature.get("type") != "Feature":
        raise ValueError("Registry item must be a GeoJSON Feature")

    properties = feature.get("properties") or {}
    catalyst_id = str(properties.get("catalyst_id") or "").strip()
    if not catalyst_id:
        raise ValueError("Registry feature missing catalyst_id")

    observed_raw = properties.get("observed_date")
    observed_date = None
    if observed_raw:
        observed_date = date.fromisoformat(str(observed_raw))

    evidence = GeometryEvidence(
        source=str(properties.get("source") or "").strip(),
        feature_name=str(properties.get("feature_name") or "").strip(),
        geometry_geojson=feature.get("geometry") or {},
        observed_date=observed_date,
        source_url=properties.get("source_url"),
        feature_id=properties.get("feature_id"),
        confidence=float(properties.get("confidence", 50.0)),
        geometry_role=str(
            properties.get("geometry_role") or "observed_geometry"
        ),
    )

    return GeometryRegistryEntry(
        catalyst_id=catalyst_id,
        evidence=evidence,
        manual_verified=bool(properties.get("manual_verified", False)),
    )


def registry_to_feature_collection(
    entries: Iterable[GeometryRegistryEntry],
) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [entry_to_feature(entry) for entry in entries],
    }


def registry_from_feature_collection(
    payload: dict[str, Any],
) -> list[GeometryRegistryEntry]:
    if payload.get("type") != "FeatureCollection":
        raise ValueError("Geometry registry must be a GeoJSON FeatureCollection")
    return [
        feature_to_entry(feature)
        for feature in payload.get("features", [])
    ]


def save_geometry_registry(
    entries: Iterable[GeometryRegistryEntry],
    path: str | Path,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = registry_to_feature_collection(entries)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_geometry_registry(
    path: str | Path,
) -> list[GeometryRegistryEntry]:
    path = Path(path)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return registry_from_feature_collection(payload)

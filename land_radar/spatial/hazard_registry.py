from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

from ..hazard import HazardGeometry, HazardSeverity


_SEVERITY_BY_TEXT = {
    "NONE": HazardSeverity.NONE,
    "LOW": HazardSeverity.LOW,
    "MEDIUM": HazardSeverity.MEDIUM,
    "HIGH": HazardSeverity.HIGH,
    "CRITICAL": HazardSeverity.CRITICAL,
}


def _parse_severity(value: Any) -> HazardSeverity:
    if isinstance(value, HazardSeverity):
        return value
    if isinstance(value, int):
        return HazardSeverity(value)
    text = str(value or "").strip().upper()
    if text in _SEVERITY_BY_TEXT:
        return _SEVERITY_BY_TEXT[text]
    raise ValueError(f"Unsupported hazard severity: {value}")


def feature_to_hazard(feature: dict[str, Any]) -> HazardGeometry:
    if feature.get("type") != "Feature":
        raise ValueError("Hazard registry item must be a GeoJSON Feature")

    props = feature.get("properties") or {}
    hazard_id = str(props.get("hazard_id") or "").strip()
    category = str(props.get("category") or "").strip()
    source = str(props.get("source") or "").strip()
    if not hazard_id or not category or not source:
        raise ValueError("Hazard feature requires hazard_id, category and source")

    observed_raw = props.get("observed_date")
    observed_date = date.fromisoformat(str(observed_raw)) if observed_raw else None

    return HazardGeometry(
        hazard_id=hazard_id,
        category=category,
        severity=_parse_severity(props.get("severity")),
        geometry_geojson=feature.get("geometry") or {},
        source=source,
        observed_date=observed_date,
        source_url=props.get("source_url"),
        hard_veto=bool(props.get("hard_veto", False)),
        confidence=float(props.get("confidence", 50.0)),
        note=str(props.get("note") or ""),
    )


def hazard_to_feature(hazard: HazardGeometry) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": hazard.geometry_geojson,
        "properties": {
            "hazard_id": hazard.hazard_id,
            "category": hazard.category,
            "severity": hazard.severity.name,
            "source": hazard.source,
            "observed_date": (
                hazard.observed_date.isoformat()
                if hazard.observed_date is not None
                else None
            ),
            "source_url": hazard.source_url,
            "hard_veto": hazard.hard_veto,
            "confidence": hazard.confidence,
            "note": hazard.note,
        },
    }


def hazards_from_feature_collection(
    payload: dict[str, Any],
) -> list[HazardGeometry]:
    if payload.get("type") != "FeatureCollection":
        raise ValueError("Hazard registry must be a GeoJSON FeatureCollection")
    return [
        feature_to_hazard(feature)
        for feature in payload.get("features", [])
    ]


def hazards_to_feature_collection(
    hazards: Iterable[HazardGeometry],
) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [hazard_to_feature(hazard) for hazard in hazards],
    }


def load_hazard_registry(path: str | Path) -> list[HazardGeometry]:
    path = Path(path)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return hazards_from_feature_collection(payload)


def save_hazard_registry(
    hazards: Iterable[HazardGeometry],
    path: str | Path,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = hazards_to_feature_collection(hazards)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

from ..planning import LegalEffect, PlanningConstraint


def _parse_effect(value: Any) -> LegalEffect:
    if isinstance(value, LegalEffect):
        return value
    if isinstance(value, int):
        return LegalEffect(value)
    text = str(value or "").strip().upper()
    try:
        return LegalEffect[text]
    except KeyError as exc:
        raise ValueError(f"Unsupported legal effect: {value}") from exc


def constraint_to_feature(
    constraint: PlanningConstraint,
) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": constraint.geometry_geojson,
        "properties": {
            "constraint_id": constraint.constraint_id,
            "category": constraint.category,
            "source": constraint.source,
            "legal_effect": constraint.legal_effect.name,
            "observed_date": (
                constraint.observed_date.isoformat()
                if constraint.observed_date is not None
                else None
            ),
            "effective_date": (
                constraint.effective_date.isoformat()
                if constraint.effective_date is not None
                else None
            ),
            "source_url": constraint.source_url,
            "hard_veto": constraint.hard_veto,
            "confidence": constraint.confidence,
            "note": constraint.note,
            "source_properties": constraint.properties,
        },
    }


def feature_to_constraint(
    feature: dict[str, Any],
) -> PlanningConstraint:
    if feature.get("type") != "Feature":
        raise ValueError("Planning registry item must be a GeoJSON Feature")

    props = feature.get("properties") or {}
    observed = props.get("observed_date")
    effective = props.get("effective_date")

    return PlanningConstraint(
        constraint_id=str(props.get("constraint_id") or "").strip(),
        category=str(props.get("category") or "").strip(),
        geometry_geojson=feature.get("geometry") or {},
        source=str(props.get("source") or "").strip(),
        legal_effect=_parse_effect(props.get("legal_effect", "REVIEW_REQUIRED")),
        observed_date=date.fromisoformat(str(observed)) if observed else None,
        effective_date=date.fromisoformat(str(effective)) if effective else None,
        source_url=props.get("source_url"),
        hard_veto=bool(props.get("hard_veto", False)),
        confidence=float(props.get("confidence", 50.0)),
        note=str(props.get("note") or ""),
        properties=dict(props.get("source_properties") or {}),
    )


def constraints_to_feature_collection(
    constraints: Iterable[PlanningConstraint],
) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [
            constraint_to_feature(constraint)
            for constraint in constraints
        ],
    }


def constraints_from_feature_collection(
    payload: dict[str, Any],
) -> list[PlanningConstraint]:
    if payload.get("type") != "FeatureCollection":
        raise ValueError(
            "Planning registry must be a GeoJSON FeatureCollection"
        )
    return [
        feature_to_constraint(feature)
        for feature in payload.get("features", [])
    ]


def save_planning_registry(
    constraints: Iterable[PlanningConstraint],
    path: str | Path,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            constraints_to_feature_collection(constraints),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def load_planning_registry(
    path: str | Path,
) -> list[PlanningConstraint]:
    path = Path(path)
    if not path.exists():
        return []
    return constraints_from_feature_collection(
        json.loads(path.read_text(encoding="utf-8"))
    )

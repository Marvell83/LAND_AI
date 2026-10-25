from __future__ import annotations

from dataclasses import asdict
from datetime import date
import json
from pathlib import Path
from typing import Iterable

from .plan_evidence import PlanEvidence, PlanStage, plan_type_normalized


DATE_FIELDS = (
    "published_date",
    "decision_date",
    "effective_date",
    "suspension_start",
    "suspension_end",
    "observed_date",
)


def _date_or_none(value):
    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def plan_to_dict(plan: PlanEvidence) -> dict:
    payload = asdict(plan)
    payload["stage"] = plan.stage.name
    for field in DATE_FIELDS:
        value = getattr(plan, field)
        payload[field] = value.isoformat() if value is not None else None
    return payload


def plan_from_dict(payload: dict) -> PlanEvidence:
    stage_value = payload.get("stage", "UNKNOWN")
    stage = (
        stage_value
        if isinstance(stage_value, PlanStage)
        else PlanStage[str(stage_value).strip().upper()]
    )
    return PlanEvidence(
        plan_id=str(payload.get("plan_id") or "").strip(),
        title=str(payload.get("title") or "").strip(),
        plan_type=plan_type_normalized(payload.get("plan_type") or ""),
        stage=stage,
        source=str(payload.get("source") or "").strip(),
        source_url=str(payload.get("source_url") or "").strip(),
        scale_denominator=(
            int(payload["scale_denominator"])
            if payload.get("scale_denominator") not in (None, "")
            else None
        ),
        published_date=_date_or_none(payload.get("published_date")),
        decision_date=_date_or_none(payload.get("decision_date")),
        effective_date=_date_or_none(payload.get("effective_date")),
        suspension_start=_date_or_none(payload.get("suspension_start")),
        suspension_end=_date_or_none(payload.get("suspension_end")),
        observed_date=_date_or_none(payload.get("observed_date")),
        confidence=float(payload.get("confidence", 50.0)),
        geometry_verified=bool(payload.get("geometry_verified", False)),
        note=str(payload.get("note") or ""),
        properties=dict(payload.get("properties") or {}),
    )


def filter_point_in_time(
    plans: Iterable[PlanEvidence],
    *,
    as_of_date: date,
) -> list[PlanEvidence]:
    """Exclude plan evidence that was not knowable by the analysis cutoff."""
    output: list[PlanEvidence] = []
    for plan in plans:
        evidence_date = (
            plan.published_date
            or plan.observed_date
            or plan.decision_date
            or plan.effective_date
        )
        if evidence_date is None:
            continue
        if evidence_date <= as_of_date:
            output.append(plan)
    return output


def save_plan_registry(
    plans: Iterable[PlanEvidence],
    path: str | Path,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema": "land-radar-plan-registry-v1",
                "plans": [plan_to_dict(plan) for plan in plans],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def load_plan_registry(path: str | Path) -> list[PlanEvidence]:
    path = Path(path)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "land-radar-plan-registry-v1":
        raise ValueError("Unsupported plan registry schema")
    return [
        plan_from_dict(item)
        for item in payload.get("plans", [])
    ]

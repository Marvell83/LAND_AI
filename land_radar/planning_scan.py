from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path

import pandas as pd

from .plan_evidence import PlanStage
from .plan_registry import filter_point_in_time, load_plan_registry
from .providers.tucbs_plan_wms import services_for_point


@dataclass(frozen=True)
class PlanningScanResult:
    candidate_count: int
    wms_covered_count: int
    registry_match_count: int
    planning_known_count: int
    output_csv: str
    summary_json: str


def _scope_matches(plan, row: dict) -> bool:
    props = plan.properties or {}
    cell_id = str(row.get("cell_id") or "")

    if props.get("cell_id"):
        return str(props["cell_id"]) == cell_id

    lat = row.get("center_lat")
    lon = row.get("center_lon")
    min_lon = props.get("min_lon")
    min_lat = props.get("min_lat")
    max_lon = props.get("max_lon")
    max_lat = props.get("max_lat")

    if all(
        value is not None
        for value in (lat, lon, min_lon, min_lat, max_lon, max_lat)
    ):
        return (
            float(min_lon) <= float(lon) <= float(max_lon)
            and float(min_lat) <= float(lat) <= float(max_lat)
        )

    return False


def run_planning_scan(
    *,
    candidate_csv: str | Path = "data/output/deep_scan/deep_scan_top30.csv",
    plan_registry_path: str | Path | None = "data/processed/plan_registry.json",
    output_dir: str | Path = "data/output/planning_scan",
    as_of_date: date,
) -> PlanningScanResult:
    candidate_path = Path(candidate_csv)
    if not candidate_path.exists():
        raise FileNotFoundError(f"Candidate CSV not found: {candidate_path}")

    frame = pd.read_csv(candidate_path)
    required = {"cell_id", "center_lat", "center_lon"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(
            "Candidate CSV missing columns: " + ", ".join(missing)
        )

    plans = []
    registry_checked = False
    if plan_registry_path is not None:
        registry_path = Path(plan_registry_path)
        if registry_path.exists():
            plans = filter_point_in_time(
                load_plan_registry(registry_path),
                as_of_date=as_of_date,
            )
            registry_checked = True

    rows: list[dict] = []
    for row in frame.to_dict(orient="records"):
        cell_id = str(row["cell_id"])
        lat = float(row["center_lat"])
        lon = float(row["center_lon"])

        services = services_for_point(lat, lon)
        matched_plans = [
            plan
            for plan in plans
            if _scope_matches(plan, row)
        ]

        final_uip_nip = [
            plan
            for plan in matched_plans
            if plan.plan_type in {"UIP", "NIP"}
            and plan.stage == PlanStage.FINALIZED
            and plan.geometry_verified
        ]
        active_non_cancelled = [
            plan
            for plan in matched_plans
            if plan.stage != PlanStage.CANCELLED
        ]

        # Planning/legal is complete only when the dedicated e-Plan/UIP/NIP
        # channel has a verified spatial record. Regional CDP WMS coverage is
        # useful context but is not sufficient for parcel-level planning status.
        planning_known = bool(final_uip_nip)

        rows.append(
            {
                "cell_id": cell_id,
                "checked": True,
                "as_of_date": as_of_date.isoformat(),
                "cdp_wms_covered": bool(services),
                "cdp_wms_services": ", ".join(
                    service.service_id for service in services
                ),
                "cdp_wms_labels": " | ".join(
                    service.label for service in services
                ),
                "plan_registry_checked": registry_checked,
                "registry_match_count": len(matched_plans),
                "active_plan_count": len(active_non_cancelled),
                "finalized_uip_nip_verified_count": len(final_uip_nip),
                "planning_known": planning_known,
                "eplan_gap": not planning_known,
                "matched_plan_ids": ", ".join(
                    plan.plan_id for plan in matched_plans
                ),
                "matched_plan_stages": ", ".join(
                    plan.stage.name for plan in matched_plans
                ),
                "note": (
                    "CDP WMS coverage is regional context only. planning_known "
                    "requires a spatially verified finalized UIP/NIP record."
                ),
            }
        )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "planning_top30.csv"
    summary_json = output_dir / "planning_scan_summary.json"

    result_frame = pd.DataFrame(rows)
    result_frame.to_csv(
        output_csv,
        index=False,
        encoding="utf-8-sig",
    )

    wms_covered_count = int(result_frame["cdp_wms_covered"].sum())
    registry_match_count = int(
        (result_frame["registry_match_count"] > 0).sum()
    )
    planning_known_count = int(result_frame["planning_known"].sum())

    summary_json.write_text(
        json.dumps(
            {
                "candidate_count": len(result_frame),
                "as_of_date": as_of_date.isoformat(),
                "wms_covered_count": wms_covered_count,
                "registry_checked": registry_checked,
                "registry_match_candidate_count": registry_match_count,
                "planning_known_count": planning_known_count,
                "known_rule": (
                    "planning_known requires at least one point-in-time-valid, "
                    "spatially verified, FINALIZED UIP/NIP plan evidence record."
                ),
                "warning": (
                    "Regional CDP WMS coverage is context, not proof of parcel "
                    "zoning or development rights."
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return PlanningScanResult(
        candidate_count=len(result_frame),
        wms_covered_count=wms_covered_count,
        registry_match_count=registry_match_count,
        planning_known_count=planning_known_count,
        output_csv=str(output_csv),
        summary_json=str(summary_json),
    )

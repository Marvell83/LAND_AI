from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import pandas as pd


CORE_EVIDENCE_LAYERS = (
    "urban_history",
    "terrain",
    "hazard",
    "catalyst",
    "sentinel_recent_change",
    "planning_legal",
    "price",
)


@dataclass(frozen=True)
class EvidencePacketBuildResult:
    candidate_count: int
    output_master_json: str
    output_matrix_csv: str
    output_packet_dir: str


def _optional(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _reason_set(value: Any) -> set[str]:
    if value is None or pd.isna(value):
        return set()
    return {
        item.strip()
        for item in str(value).split(",")
        if item.strip()
    }


def _table_by_cell(
    path: Path | None,
    *,
    label: str,
) -> dict[str, dict]:
    if path is None or not path.exists():
        return {}
    frame = pd.read_csv(path)
    if "cell_id" not in frame.columns:
        raise ValueError(f"{label} CSV missing cell_id")
    return {
        str(row["cell_id"]): {
            key: _optional(value)
            for key, value in row.items()
            if key != "cell_id"
        }
        for row in frame.to_dict(orient="records")
    }


def build_evidence_packets(
    *,
    deep_scan_csv: str | Path = "data/output/deep_scan/deep_scan_top30.csv",
    first_scan_csv: str | Path | None = "data/output/first_scan/ghsl_top_candidates.csv",
    sentinel_csv: str | Path | None = "data/output/sentinel_confirm/sentinel_top30_change.csv",
    protected_csv: str | Path | None = "data/output/official_constraints/protected_area_top30.csv",
    flood_csv: str | Path | None = "data/output/official_constraints/flood_risk_top30.csv",
    landslide_csv: str | Path | None = "data/output/landslide_scan/landslide_top30.csv",
    price_csv: str | Path | None = "data/output/price_scan/price_top30.csv",
    planning_csv: str | Path | None = "data/output/planning_scan/planning_top30.csv",
    kgm_highway_csv: str | Path | None = "data/output/kgm_highway_scan/kgm_highway_top30.csv",
    output_dir: str | Path = "data/output/evidence_packets",
) -> EvidencePacketBuildResult:
    deep_path = Path(deep_scan_csv)
    if not deep_path.exists():
        raise FileNotFoundError(f"Deep-scan CSV not found: {deep_path}")

    deep = pd.read_csv(deep_path)
    required = {
        "cell_id",
        "center_lat",
        "center_lon",
        "urban_rank",
        "acceleration_pp_per_year",
        "cagr_2015_2020_pct",
        "p90_slope_deg",
        "nearest_catalyst_km",
        "catalyst_stage_max",
        "hard_veto",
        "max_hazard_severity",
        "status",
        "reasons",
    }
    missing = sorted(required - set(deep.columns))
    if missing:
        raise ValueError(
            "Deep-scan CSV missing columns: " + ", ".join(missing)
        )

    first_scan_path = (
        Path(first_scan_csv)
        if first_scan_csv is not None
        else None
    )
    sentinel_path = (
        Path(sentinel_csv)
        if sentinel_csv is not None
        else None
    )
    protected_path = (
        Path(protected_csv)
        if protected_csv is not None
        else None
    )
    flood_path = (
        Path(flood_csv)
        if flood_csv is not None
        else None
    )
    landslide_path = (
        Path(landslide_csv)
        if landslide_csv is not None
        else None
    )
    price_path = (
        Path(price_csv)
        if price_csv is not None
        else None
    )
    planning_path = (
        Path(planning_csv)
        if planning_csv is not None
        else None
    )
    kgm_highway_path = (
        Path(kgm_highway_csv)
        if kgm_highway_csv is not None
        else None
    )
    first_scan = _table_by_cell(
        first_scan_path,
        label="First-scan",
    )
    sentinel = _table_by_cell(
        sentinel_path,
        label="Sentinel evidence",
    )
    protected = _table_by_cell(
        protected_path,
        label="Protected-area evidence",
    )
    flood = _table_by_cell(
        flood_path,
        label="Flood evidence",
    )
    landslide = _table_by_cell(
        landslide_path,
        label="Landslide evidence",
    )
    price = _table_by_cell(
        price_path,
        label="Price evidence",
    )
    planning = _table_by_cell(
        planning_path,
        label="Planning evidence",
    )
    kgm_highway = _table_by_cell(
        kgm_highway_path,
        label="KGM highway evidence",
    )

    output_dir = Path(output_dir)
    packet_dir = output_dir / "cells"
    packet_dir.mkdir(parents=True, exist_ok=True)

    packets: list[dict] = []
    matrix_rows: list[dict] = []

    for row in deep.to_dict(orient="records"):
        cell_id = str(row["cell_id"])
        reasons = _reason_set(row.get("reasons"))
        first_scan_row = first_scan.get(cell_id, {})
        sentinel_row = sentinel.get(cell_id)
        protected_row = protected.get(cell_id)
        flood_row = flood.get(cell_id)
        landslide_row = landslide.get(cell_id)
        price_row = price.get(cell_id)
        planning_row = planning.get(cell_id)
        kgm_highway_row = kgm_highway.get(cell_id)

        protected_checked = bool(
            protected_row
            and protected_row.get("checked") in (True, 1, "True", "true")
        )
        flood_checked = bool(
            flood_row
            and flood_row.get("checked") in (True, 1, "True", "true")
        )
        landslide_checked = bool(
            landslide_row
            and landslide_row.get("checked") in (True, 1, "True", "true")
        )
        price_checked = bool(
            price_row
            and price_row.get("checked") in (True, 1, "True", "true")
        )
        price_known = bool(
            price_row
            and price_row.get("known") in (True, 1, "True", "true")
        )
        planning_checked = bool(
            planning_row
            and planning_row.get("checked") in (True, 1, "True", "true")
        )
        planning_known = bool(
            planning_row
            and planning_row.get("planning_known") in (True, 1, "True", "true")
        )

        base_hazard_known = "hazard_unknown" not in reasons
        official_core_hazard_known = flood_checked and landslide_checked

        layer_known = {
            "urban_history": (
                _optional(row.get("acceleration_pp_per_year")) is not None
            ),
            "terrain": (
                "terrain_unknown" not in reasons
                and _optional(row.get("p90_slope_deg")) is not None
            ),
            "hazard": base_hazard_known or official_core_hazard_known,
            "catalyst": (
                "catalyst_unknown" not in reasons
                and _optional(row.get("nearest_catalyst_km")) is not None
            ),
            "sentinel_recent_change": sentinel_row is not None,
            "planning_legal": planning_known,
            "price": price_known,
        }

        known_count = sum(layer_known.values())
        coverage_pct = round(
            known_count / len(CORE_EVIDENCE_LAYERS) * 100.0,
            1,
        )
        missing_layers = [
            layer
            for layer in CORE_EVIDENCE_LAYERS
            if not layer_known[layer]
        ]

        packet = {
            "cell_id": cell_id,
            "location": {
                "lat": float(row["center_lat"]),
                "lon": float(row["center_lon"]),
            },
            "funnel": {
                "status": str(row["status"]),
                "reasons": sorted(reasons),
                "urban_rank": int(row["urban_rank"]),
            },
            "urban_history": {
                "built_2010_m2": _optional(
                    first_scan_row.get("built_2010_m2")
                ),
                "built_2015_m2": _optional(
                    first_scan_row.get("built_2015_m2")
                ),
                "built_2020_m2": _optional(
                    first_scan_row.get("built_2020_m2")
                ),
                "cagr_2010_2015_pct": _optional(
                    first_scan_row.get("cagr_2010_2015_pct")
                ),
                "cagr_2015_2020_pct": _optional(
                    row.get("cagr_2015_2020_pct")
                ),
                "acceleration_pp_per_year": _optional(
                    row.get("acceleration_pp_per_year")
                ),
                "occupied_share_acceleration_pp": _optional(
                    first_scan_row.get("occupied_share_acceleration_pp")
                ),
                "signal": _optional(first_scan_row.get("signal")),
            },
            "terrain": {
                "p90_slope_deg": _optional(row.get("p90_slope_deg")),
                "known": layer_known["terrain"],
            },
            "hazard": {
                "hard_veto": bool(row.get("hard_veto", False)),
                "max_hazard_severity": _optional(
                    row.get("max_hazard_severity")
                ),
                "known": layer_known["hazard"],
                "official_flood": {
                    "checked": flood_checked,
                    "finding_count": (
                        _optional(flood_row.get("finding_count"))
                        if flood_row
                        else None
                    ),
                    "max_severity": (
                        _optional(flood_row.get("max_severity"))
                        if flood_row
                        else None
                    ),
                    "max_overlap_ratio": (
                        _optional(flood_row.get("max_overlap_ratio"))
                        if flood_row
                        else None
                    ),
                    "nearest_hazard_km": (
                        _optional(flood_row.get("nearest_hazard_km"))
                        if flood_row
                        else None
                    ),
                    "note": "Official USBS flood-risk polygon check.",
                },
                "official_landslide_inventory": {
                    "checked": landslide_checked,
                    "finding_count": (
                        _optional(landslide_row.get("finding_count"))
                        if landslide_row
                        else None
                    ),
                    "max_overlap_ratio": (
                        _optional(landslide_row.get("max_overlap_ratio"))
                        if landslide_row
                        else None
                    ),
                    "nearest_hazard_km": (
                        _optional(landslide_row.get("nearest_hazard_km"))
                        if landslide_row
                        else None
                    ),
                    "note": (
                        "MTA/TUCBS landslide inventory check. Inventory is not "
                        "the same as AFAD landslide susceptibility."
                    ),
                },
                "core_hazard_coverage": {
                    "known": official_core_hazard_known,
                    "policy": (
                        "Known when USBS flood and MTA landslide inventory have "
                        "both been checked, or a separate verified hazard registry "
                        "already covered the candidate."
                    ),
                    "afad_susceptibility": "restricted_or_not_configured",
                },
            },
            "catalyst": {
                "nearest_catalyst_km": _optional(
                    row.get("nearest_catalyst_km")
                ),
                "max_stage": _optional(
                    row.get("catalyst_stage_max")
                ),
                "known": layer_known["catalyst"],
                "kgm_highway": {
                    "status_checked": bool(
                        kgm_highway_row
                        and kgm_highway_row.get("status_checked")
                        in (True, 1, "True", "true")
                    ),
                    "geometry_registry_checked": bool(
                        kgm_highway_row
                        and kgm_highway_row.get("geometry_registry_checked")
                        in (True, 1, "True", "true")
                    ),
                    "spatial_known": bool(
                        kgm_highway_row
                        and kgm_highway_row.get("spatial_known")
                        in (True, 1, "True", "true")
                    ),
                    "linked_project_count": (
                        _optional(kgm_highway_row.get("linked_project_count"))
                        if kgm_highway_row
                        else None
                    ),
                    "nearest_project_id": (
                        _optional(kgm_highway_row.get("nearest_project_id"))
                        if kgm_highway_row
                        else None
                    ),
                    "nearest_project_name": (
                        _optional(kgm_highway_row.get("nearest_project_name"))
                        if kgm_highway_row
                        else None
                    ),
                    "nearest_project_stage": (
                        _optional(kgm_highway_row.get("nearest_project_stage"))
                        if kgm_highway_row
                        else None
                    ),
                    "nearest_project_distance_km": (
                        _optional(
                            kgm_highway_row.get("nearest_project_distance_km")
                        )
                        if kgm_highway_row
                        else None
                    ),
                    "nearest_influence_code": (
                        _optional(kgm_highway_row.get("nearest_influence_code"))
                        if kgm_highway_row
                        else None
                    ),
                    "note": (
                        "KGM project status and route geometry are separate. "
                        "spatial_known requires a matching geometry-registry entry."
                    ),
                },
            },
            "sentinel_recent_change": sentinel_row,
            "planning_legal": {
                "known": planning_known,
                "protected_area": {
                    "checked": protected_checked,
                    "finding_count": (
                        _optional(protected_row.get("finding_count"))
                        if protected_row
                        else None
                    ),
                    "intersecting_count": (
                        _optional(protected_row.get("intersecting_count"))
                        if protected_row
                        else None
                    ),
                    "legal_review_required": (
                        bool(protected_row.get("legal_review_required"))
                        if protected_row
                        else None
                    ),
                    "max_overlap_ratio": (
                        _optional(protected_row.get("max_overlap_ratio"))
                        if protected_row
                        else None
                    ),
                    "nearest_constraint_km": (
                        _optional(protected_row.get("nearest_constraint_km"))
                        if protected_row
                        else None
                    ),
                },
                "eplan": {
                    "checked": planning_checked,
                    "planning_known": planning_known,
                    "cdp_wms_covered": (
                        bool(planning_row.get("cdp_wms_covered"))
                        if planning_row
                        else None
                    ),
                    "cdp_wms_services": (
                        _optional(planning_row.get("cdp_wms_services"))
                        if planning_row
                        else None
                    ),
                    "registry_match_count": (
                        _optional(planning_row.get("registry_match_count"))
                        if planning_row
                        else None
                    ),
                    "active_plan_count": (
                        _optional(planning_row.get("active_plan_count"))
                        if planning_row
                        else None
                    ),
                    "finalized_uip_nip_verified_count": (
                        _optional(
                            planning_row.get("finalized_uip_nip_verified_count")
                        )
                        if planning_row
                        else None
                    ),
                    "matched_plan_ids": (
                        _optional(planning_row.get("matched_plan_ids"))
                        if planning_row
                        else None
                    ),
                    "matched_plan_stages": (
                        _optional(planning_row.get("matched_plan_stages"))
                        if planning_row
                        else None
                    ),
                    "note": (
                        "CDP WMS coverage is context only. planning_known "
                        "requires finalized spatially verified UIP/NIP evidence."
                    ),
                },
                "note": (
                    "planning_legal is complete only when the e-Plan/UIP/NIP "
                    "channel satisfies LAND RADAR's verified-final-plan rule."
                ),
            },
            "price": {
                "checked": price_checked,
                "known": price_known,
                "price_basis": (
                    _optional(price_row.get("price_basis"))
                    if price_row
                    else None
                ),
                "used_rows": (
                    _optional(price_row.get("used_rows"))
                    if price_row
                    else None
                ),
                "median_price_per_m2": (
                    _optional(price_row.get("median_price_per_m2"))
                    if price_row
                    else None
                ),
                "p25_price_per_m2": (
                    _optional(price_row.get("p25_price_per_m2"))
                    if price_row
                    else None
                ),
                "p75_price_per_m2": (
                    _optional(price_row.get("p75_price_per_m2"))
                    if price_row
                    else None
                ),
                "dispersion_ratio": (
                    _optional(price_row.get("dispersion_ratio"))
                    if price_row
                    else None
                ),
                "median_age_days": (
                    _optional(price_row.get("median_age_days"))
                    if price_row
                    else None
                ),
                "confidence_label": (
                    _optional(price_row.get("confidence_label"))
                    if price_row
                    else None
                ),
                "reason": (
                    _optional(price_row.get("reason"))
                    if price_row
                    else "No cell-specific comparable dataset attached."
                ),
                "note": (
                    "Price known requires MEDIUM/HIGH comparable-data confidence. "
                    "This remains a local market reference, not a parcel valuation."
                ),
            },
            "evidence_coverage": {
                "known_layers": known_count,
                "total_layers": len(CORE_EVIDENCE_LAYERS),
                "coverage_pct": coverage_pct,
                "missing_layers": missing_layers,
                "warning": (
                    "Evidence coverage measures data completeness only. "
                    "It is not an opportunity or investment score."
                ),
            },
        }
        packets.append(packet)

        packet_path = packet_dir / f"{cell_id}.json"
        packet_path.write_text(
            json.dumps(packet, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        matrix_rows.append(
            {
                "cell_id": cell_id,
                "lat": float(row["center_lat"]),
                "lon": float(row["center_lon"]),
                "status": str(row["status"]),
                "urban_rank": int(row["urban_rank"]),
                "acceleration_pp_per_year": _optional(
                    row.get("acceleration_pp_per_year")
                ),
                "p90_slope_deg": _optional(row.get("p90_slope_deg")),
                "hard_veto": bool(row.get("hard_veto", False)),
                "nearest_catalyst_km": _optional(
                    row.get("nearest_catalyst_km")
                ),
                "sentinel_known": layer_known["sentinel_recent_change"],
                "protected_area_checked": protected_checked,
                "flood_checked": flood_checked,
                "planning_checked": planning_checked,
                "planning_known": planning_known,
                "price_checked": price_checked,
                "price_known": price_known,
                "evidence_coverage_pct": coverage_pct,
                "missing_layers": ", ".join(missing_layers),
            }
        )

    master_path = output_dir / "candidate_evidence_packets.json"
    matrix_path = output_dir / "candidate_evidence_matrix.csv"

    master_path.write_text(
        json.dumps(
            {
                "candidate_count": len(packets),
                "layers": list(CORE_EVIDENCE_LAYERS),
                "warning": (
                    "Evidence coverage is data completeness, not an investment score."
                ),
                "candidates": packets,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    pd.DataFrame(matrix_rows).to_csv(
        matrix_path,
        index=False,
        encoding="utf-8-sig",
    )

    return EvidencePacketBuildResult(
        candidate_count=len(packets),
        output_master_json=str(master_path),
        output_matrix_csv=str(matrix_path),
        output_packet_dir=str(packet_dir),
    )

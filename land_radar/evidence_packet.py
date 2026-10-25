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


def _sentinel_by_cell(path: Path | None) -> dict[str, dict]:
    if path is None or not path.exists():
        return {}
    frame = pd.read_csv(path)
    if "cell_id" not in frame.columns:
        raise ValueError("Sentinel evidence CSV missing cell_id")
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
    sentinel_csv: str | Path | None = "data/output/sentinel_confirm/sentinel_top30_change.csv",
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

    sentinel_path = (
        Path(sentinel_csv)
        if sentinel_csv is not None
        else None
    )
    sentinel = _sentinel_by_cell(sentinel_path)

    output_dir = Path(output_dir)
    packet_dir = output_dir / "cells"
    packet_dir.mkdir(parents=True, exist_ok=True)

    packets: list[dict] = []
    matrix_rows: list[dict] = []

    for row in deep.to_dict(orient="records"):
        cell_id = str(row["cell_id"])
        reasons = _reason_set(row.get("reasons"))
        sentinel_row = sentinel.get(cell_id)

        layer_known = {
            "urban_history": (
                _optional(row.get("acceleration_pp_per_year")) is not None
            ),
            "terrain": (
                "terrain_unknown" not in reasons
                and _optional(row.get("p90_slope_deg")) is not None
            ),
            "hazard": "hazard_unknown" not in reasons,
            "catalyst": (
                "catalyst_unknown" not in reasons
                and _optional(row.get("nearest_catalyst_km")) is not None
            ),
            "sentinel_recent_change": sentinel_row is not None,
            "planning_legal": False,
            "price": False,
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
                "acceleration_pp_per_year": _optional(
                    row.get("acceleration_pp_per_year")
                ),
                "cagr_2015_2020_pct": _optional(
                    row.get("cagr_2015_2020_pct")
                ),
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
            },
            "catalyst": {
                "nearest_catalyst_km": _optional(
                    row.get("nearest_catalyst_km")
                ),
                "max_stage": _optional(
                    row.get("catalyst_stage_max")
                ),
                "known": layer_known["catalyst"],
            },
            "sentinel_recent_change": sentinel_row,
            "planning_legal": {
                "known": False,
                "note": "Not integrated into automated candidate packet yet.",
            },
            "price": {
                "known": False,
                "note": (
                    "No cell-specific verified comparable dataset has been "
                    "attached to this candidate."
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
                "planning_known": False,
                "price_known": False,
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

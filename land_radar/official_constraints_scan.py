from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path

import pandas as pd

from .geometry import bbox_for_cell
from .grid import GridCell
from .providers.tarimorman_official import (
    fetch_flood_hazards,
    fetch_protected_constraints,
)
from .spatial.hazard_overlap import (
    batch_link_hazards,
    summarize_cell_hazards,
)
from .spatial.hazard_registry import hazards_to_feature_collection
from .spatial.planning_overlap import (
    batch_link_constraints,
    summarize_cell_planning,
)
from .spatial.planning_registry import constraints_to_feature_collection


@dataclass(frozen=True)
class OfficialConstraintScanResult:
    candidate_count: int
    protected_features: int
    flood_features: int
    protected_csv: str
    flood_csv: str
    protected_geojson: str
    flood_geojson: str
    summary_json: str


def _cells_from_deep_scan(
    path: str | Path,
    *,
    cell_km: float,
) -> list[GridCell]:
    frame = pd.read_csv(path)
    required = {"cell_id", "center_lat", "center_lon"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(
            "Deep-scan CSV missing columns: " + ", ".join(missing)
        )
    return [
        GridCell(
            cell_id=str(row.cell_id),
            center_lat=float(row.center_lat),
            center_lon=float(row.center_lon),
            size_km=cell_km,
        )
        for row in frame.itertuples(index=False)
    ]


def _envelope(
    cells: list[GridCell],
    *,
    padding_km: float = 5.0,
) -> tuple[float, float, float, float]:
    if not cells:
        raise ValueError("No candidate cells supplied")
    boxes = [
        bbox_for_cell(cell, padding_km=padding_km)
        for cell in cells
    ]
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def run_official_constraints_scan(
    *,
    deep_scan_csv: str | Path = "data/output/deep_scan/deep_scan_top30.csv",
    output_dir: str | Path = "data/output/official_constraints",
    cell_km: float = 5.0,
    query_padding_km: float = 5.0,
) -> OfficialConstraintScanResult:
    cells = _cells_from_deep_scan(
        deep_scan_csv,
        cell_km=cell_km,
    )
    bbox = _envelope(
        cells,
        padding_km=query_padding_km,
    )

    protected = fetch_protected_constraints(bbox)
    flood = fetch_flood_hazards(bbox)

    protected_links = batch_link_constraints(
        cells,
        protected,
        max_distance_km=20.0,
    )
    flood_links = batch_link_hazards(
        cells,
        flood,
        max_distance_km=20.0,
    )

    protected_rows = []
    flood_rows = []

    for cell in cells:
        planning = summarize_cell_planning(
            cell.cell_id,
            protected_links,
            checked=True,
        )
        protected_rows.append(
            {
                "cell_id": cell.cell_id,
                "checked": planning.checked,
                "finding_count": planning.finding_count,
                "intersecting_count": planning.intersecting_count,
                "legal_review_required": planning.legal_review_required,
                "hard_veto": planning.hard_veto,
                "hard_veto_categories": ", ".join(
                    planning.hard_veto_categories
                ),
                "max_legal_effect": int(planning.max_legal_effect),
                "max_overlap_ratio": planning.max_overlap_ratio,
                "nearest_constraint_km": planning.nearest_constraint_km,
            }
        )

        hazard = summarize_cell_hazards(
            cell.cell_id,
            flood_links,
        )
        flood_rows.append(
            {
                "cell_id": cell.cell_id,
                "checked": True,
                "finding_count": hazard.finding_count,
                "hard_veto": hazard.hard_veto,
                "hard_veto_categories": ", ".join(
                    hazard.hard_veto_categories
                ),
                "max_severity": int(hazard.max_severity),
                "max_overlap_ratio": hazard.max_overlap_ratio,
                "nearest_hazard_km": hazard.nearest_hazard_km,
            }
        )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    protected_csv = output_dir / "protected_area_top30.csv"
    flood_csv = output_dir / "flood_risk_top30.csv"
    protected_geojson = output_dir / "protected_area_features.geojson"
    flood_geojson = output_dir / "flood_risk_features.geojson"
    summary_json = output_dir / "official_constraints_summary.json"

    pd.DataFrame(protected_rows).to_csv(
        protected_csv,
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(flood_rows).to_csv(
        flood_csv,
        index=False,
        encoding="utf-8-sig",
    )

    protected_geojson.write_text(
        json.dumps(
            constraints_to_feature_collection(protected),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    flood_geojson.write_text(
        json.dumps(
            hazards_to_feature_collection(flood),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    summary = {
        "candidate_count": len(cells),
        "query_bbox": list(bbox),
        "protected_feature_count": len(protected),
        "flood_feature_count": len(flood),
        "protected_source_checked": True,
        "flood_source_checked": True,
        "eplan_checked": False,
        "warning": (
            "Protected-area overlap requires legal review but is not an "
            "automatic hard veto. Flood risk polygons are evidence, not an "
            "automatic parcel exclusion. e-Plan zoning remains unchecked."
        ),
    }
    summary_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return OfficialConstraintScanResult(
        candidate_count=len(cells),
        protected_features=len(protected),
        flood_features=len(flood),
        protected_csv=str(protected_csv),
        flood_csv=str(flood_csv),
        protected_geojson=str(protected_geojson),
        flood_geojson=str(flood_geojson),
        summary_json=str(summary_json),
    )

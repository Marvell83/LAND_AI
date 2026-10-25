from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Mapping

import pandas as pd

from .candidate_funnel import (
    CandidatePolicy,
    CandidateRecord,
    build_candidate_funnel,
    surviving_candidates,
)
from .catalyst import Catalyst
from .grid import GridCell
from .providers.copernicus_dem import TerrainSummary
from .spatial.batch import batch_link_catalysts
from .spatial.hazard_overlap import (
    batch_link_hazards,
    summarize_cell_hazards,
)
from .spatial.hazard_registry import load_hazard_registry
from .spatial.registry import load_geometry_registry
from .terrain_scan import TerrainClient, scan_terrain
from .urban_scan import UrbanScanRecord


@dataclass(frozen=True)
class DeepScanResult:
    input_candidates: int
    pass_count: int
    pass_with_gaps_count: int
    drop_count: int
    finalists: int
    output_full_csv: str
    output_final_csv: str
    output_final_geojson: str
    output_summary_json: str
    notes: tuple[str, ...]


def load_urban_shortlist(path: str | Path) -> list[UrbanScanRecord]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"First-scan CSV not found: {path}")

    frame = pd.read_csv(path)
    required = {
        "cell_id",
        "center_lat",
        "center_lon",
        "built_2010_m2",
        "built_2015_m2",
        "built_2020_m2",
        "cagr_2010_2015_pct",
        "cagr_2015_2020_pct",
        "acceleration_pp_per_year",
        "occupied_share_acceleration_pp",
        "signal",
    }
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(
            "First-scan CSV missing columns: " + ", ".join(missing)
        )

    records: list[UrbanScanRecord] = []
    for row in frame.to_dict(orient="records"):
        def optional_float(value):
            return None if pd.isna(value) else float(value)

        records.append(
            UrbanScanRecord(
                cell_id=str(row["cell_id"]),
                center_lat=float(row["center_lat"]),
                center_lon=float(row["center_lon"]),
                built_2010_m2=float(row["built_2010_m2"]),
                built_2015_m2=float(row["built_2015_m2"]),
                built_2020_m2=float(row["built_2020_m2"]),
                cagr_2010_2015_pct=optional_float(row["cagr_2010_2015_pct"]),
                cagr_2015_2020_pct=optional_float(row["cagr_2015_2020_pct"]),
                acceleration_pp_per_year=optional_float(
                    row["acceleration_pp_per_year"]
                ),
                occupied_share_acceleration_pp=float(
                    row["occupied_share_acceleration_pp"]
                ),
                signal=str(row["signal"]),
            )
        )
    return records


def _cells_from_urban(
    urban: list[UrbanScanRecord],
    *,
    cell_km: float,
) -> list[GridCell]:
    if cell_km <= 0:
        raise ValueError("cell_km must be positive")
    return [
        GridCell(
            cell_id=record.cell_id,
            center_lat=record.center_lat,
            center_lon=record.center_lon,
            size_km=cell_km,
        )
        for record in urban
    ]


def _candidate_row(record: CandidateRecord) -> dict:
    row = asdict(record)
    row["reasons"] = ", ".join(record.reasons)
    return row


def _candidate_feature(record: CandidateRecord) -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [
                record.center_lon,
                record.center_lat,
            ],
        },
        "properties": _candidate_row(record),
    }


def run_deep_scan(
    *,
    first_scan_csv: str | Path = "data/output/first_scan/ghsl_top_candidates.csv",
    output_dir: str | Path = "data/output/deep_scan",
    cell_km: float = 5.0,
    final_top_n: int = 30,
    terrain_client: TerrainClient | None = None,
    hazard_registry_path: str | Path | None = "data/processed/hazard_registry.geojson",
    geometry_registry_path: str | Path | None = "data/processed/geometry_registry.geojson",
    catalysts: Mapping[str, Catalyst] | None = None,
    max_p90_slope_deg: float = 12.0,
    max_catalyst_distance_km: float = 20.0,
    require_catalyst: bool = False,
) -> DeepScanResult:
    if final_top_n <= 0:
        raise ValueError("final_top_n must be positive")

    urban = load_urban_shortlist(first_scan_csv)
    if not urban:
        raise ValueError("First-scan shortlist is empty")
    cells = _cells_from_urban(urban, cell_km=cell_km)

    notes: list[str] = []

    terrain_records = []
    if terrain_client is not None:
        terrain_records = scan_terrain(
            cells,
            terrain_client,
            cache_dir="data/cache/terrain",
            dem_instance="COPERNICUS_90",
        )
    else:
        notes.append("terrain_missing")

    hazard_summaries = []
    if hazard_registry_path is not None and Path(hazard_registry_path).exists():
        hazards = load_hazard_registry(hazard_registry_path)
        links = batch_link_hazards(
            cells,
            hazards,
            max_distance_km=20.0,
        )
        hazard_summaries = [
            summarize_cell_hazards(cell.cell_id, links)
            for cell in cells
        ]
    else:
        notes.append("hazard_registry_missing")

    catalyst_links = []
    if (
        geometry_registry_path is not None
        and Path(geometry_registry_path).exists()
    ):
        entries = load_geometry_registry(geometry_registry_path)
        catalyst_map = dict(catalysts or {})
        if catalyst_map:
            result = batch_link_catalysts(
                cells,
                catalyst_map,
                entries,
                max_distance_km=max_catalyst_distance_km,
            )
            catalyst_links = list(result.links)
            if result.missing_catalysts:
                notes.append(
                    "geometry_without_status:"
                    + ",".join(result.missing_catalysts[:20])
                )
            if result.missing_geometries:
                notes.append(
                    f"status_without_geometry:{len(result.missing_geometries)}"
                )
        else:
            notes.append("catalyst_status_missing")
    else:
        notes.append("geometry_registry_missing")

    policy = CandidatePolicy(
        urban_top_n=len(urban),
        max_p90_slope_deg=max_p90_slope_deg,
        max_catalyst_distance_km=max_catalyst_distance_km,
        require_catalyst=require_catalyst,
        exclude_hard_veto=True,
    )

    funnel = build_candidate_funnel(
        urban,
        terrain_records=terrain_records,
        hazard_summaries=hazard_summaries,
        catalyst_links=catalyst_links,
        policy=policy,
    )
    survivors = surviving_candidates(funnel)
    finalists = survivors[: min(final_top_n, len(survivors))]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    full_csv = output_dir / "deep_scan_all_candidates.csv"
    final_csv = output_dir / "deep_scan_top30.csv"
    final_geojson = output_dir / "deep_scan_top30.geojson"
    summary_json = output_dir / "deep_scan_summary.json"

    pd.DataFrame(
        [_candidate_row(record) for record in funnel]
    ).to_csv(
        full_csv,
        index=False,
        encoding="utf-8-sig",
    )
    pd.DataFrame(
        [_candidate_row(record) for record in finalists]
    ).to_csv(
        final_csv,
        index=False,
        encoding="utf-8-sig",
    )

    final_geojson.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    _candidate_feature(record)
                    for record in finalists
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    pass_count = sum(record.status == "PASS" for record in funnel)
    gap_count = sum(
        record.status == "PASS_WITH_GAPS"
        for record in funnel
    )
    drop_count = sum(record.status == "DROP" for record in funnel)

    summary = {
        "input_candidates": len(urban),
        "pass_count": pass_count,
        "pass_with_gaps_count": gap_count,
        "drop_count": drop_count,
        "finalists": len(finalists),
        "notes": notes,
        "policy": {
            "max_p90_slope_deg": max_p90_slope_deg,
            "max_catalyst_distance_km": max_catalyst_distance_km,
            "require_catalyst": require_catalyst,
            "exclude_hard_veto": True,
        },
        "warning": (
            "Finalists remain research candidates. This is not an investment "
            "ranking and missing evidence remains explicit."
        ),
    }
    summary_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return DeepScanResult(
        input_candidates=len(urban),
        pass_count=pass_count,
        pass_with_gaps_count=gap_count,
        drop_count=drop_count,
        finalists=len(finalists),
        output_full_csv=str(full_csv),
        output_final_csv=str(final_csv),
        output_final_geojson=str(final_geojson),
        output_summary_json=str(summary_json),
        notes=tuple(notes),
    )

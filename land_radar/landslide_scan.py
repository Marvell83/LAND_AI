from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import pandas as pd

from .geometry import bbox_for_cell
from .grid import GridCell
from .providers.mta_landslide import (
    MTALandslideConfig,
    fetch_landslide_hazards,
)
from .spatial.hazard_overlap import (
    batch_link_hazards,
    summarize_cell_hazards,
)


@dataclass(frozen=True)
class LandslideScanResult:
    candidate_count: int
    feature_count: int
    output_csv: str
    output_geojson: str
    summary_json: str


def _cells(path: str | Path, cell_km: float) -> list[GridCell]:
    frame = pd.read_csv(path)
    required = {"cell_id", "center_lat", "center_lon"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(
            "Candidate CSV missing columns: " + ", ".join(missing)
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
    padding_km: float,
) -> tuple[float, float, float, float]:
    boxes = [bbox_for_cell(cell, padding_km=padding_km) for cell in cells]
    return (
        min(item[0] for item in boxes),
        min(item[1] for item in boxes),
        max(item[2] for item in boxes),
        max(item[3] for item in boxes),
    )


def run_landslide_scan(
    *,
    candidate_csv: str | Path = "data/output/deep_scan/deep_scan_top30.csv",
    output_dir: str | Path = "data/output/landslide_scan",
    config: MTALandslideConfig,
    cell_km: float = 5.0,
    padding_km: float = 5.0,
) -> LandslideScanResult:
    cells = _cells(candidate_csv, cell_km)
    if not cells:
        raise ValueError("Candidate CSV is empty")

    bbox = _envelope(cells, padding_km)
    hazards = fetch_landslide_hazards(bbox, config)
    links = batch_link_hazards(
        cells,
        hazards,
        max_distance_km=20.0,
    )

    rows = []
    for cell in cells:
        summary = summarize_cell_hazards(cell.cell_id, links)
        rows.append(
            {
                "cell_id": cell.cell_id,
                "checked": True,
                "finding_count": summary.finding_count,
                "hard_veto": summary.hard_veto,
                "max_severity": int(summary.max_severity),
                "max_overlap_ratio": summary.max_overlap_ratio,
                "nearest_hazard_km": summary.nearest_hazard_km,
                "note": (
                    "MTA/TUCBS heyelan envanter kontrolü. Envanter kaydı "
                    "heyelan duyarlılık sınıfı değildir."
                ),
            }
        )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_csv = output_dir / "landslide_top30.csv"
    output_geojson = output_dir / "landslide_features.geojson"
    summary_json = output_dir / "landslide_scan_summary.json"

    pd.DataFrame(rows).to_csv(
        output_csv,
        index=False,
        encoding="utf-8-sig",
    )
    output_geojson.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": hazard.geometry_geojson,
                        "properties": {
                            "hazard_id": hazard.hazard_id,
                            "category": hazard.category,
                            "source": hazard.source,
                            "severity": hazard.severity.name,
                            "hard_veto": hazard.hard_veto,
                            "confidence": hazard.confidence,
                            "note": hazard.note,
                        },
                    }
                    for hazard in hazards
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    summary_json.write_text(
        json.dumps(
            {
                "candidate_count": len(cells),
                "feature_count": len(hazards),
                "service_url": config.service_url,
                "type_name": config.type_name,
                "warning": (
                    "Landslide inventory is not equivalent to AFAD landslide "
                    "susceptibility. No automatic severity or hard veto is inferred."
                ),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return LandslideScanResult(
        candidate_count=len(cells),
        feature_count=len(hazards),
        output_csv=str(output_csv),
        output_geojson=str(output_geojson),
        summary_json=str(summary_json),
    )

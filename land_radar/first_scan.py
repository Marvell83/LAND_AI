from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

import pandas as pd

from .pilot import build_pilot_grid
from .readiness import check_data_readiness
from .urban_scan import UrbanScanRecord, rank_accelerating, scan_grid_ghsl


@dataclass(frozen=True)
class FirstScanResult:
    scanned_cells: int
    ranked_cells: int
    top_cells: int
    measurable_acceleration_cells: int
    accelerating_cells: int
    stable_cells: int
    decelerating_cells: int
    output_csv: str
    output_geojson: str
    output_summary_json: str


def _record_row(rank: int, record: UrbanScanRecord) -> dict:
    row = asdict(record)
    return {"rank": rank, **row}


def _feature(rank: int, record: UrbanScanRecord) -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [
                record.center_lon,
                record.center_lat,
            ],
        },
        "properties": _record_row(rank, record),
    }


def export_first_scan(
    ranked: Iterable[UrbanScanRecord],
    *,
    top_n: int,
    output_dir: str | Path,
) -> FirstScanResult:
    ranked_list = list(ranked)
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    if not ranked_list:
        raise ValueError("ranked scan cannot be empty")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    top = ranked_list[: min(top_n, len(ranked_list))]
    rows = [
        _record_row(rank, record)
        for rank, record in enumerate(top, start=1)
    ]

    csv_path = output_dir / "ghsl_top_candidates.csv"
    geojson_path = output_dir / "ghsl_top_candidates.geojson"
    summary_path = output_dir / "ghsl_scan_summary.json"

    pd.DataFrame(rows).to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
    )

    geojson = {
        "type": "FeatureCollection",
        "features": [
            _feature(rank, record)
            for rank, record in enumerate(top, start=1)
        ],
    }
    geojson_path.write_text(
        json.dumps(geojson, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    measurable = [
        record
        for record in ranked_list
        if record.acceleration_pp_per_year is not None
    ]
    summary = {
        "scanned_cells": len(ranked_list),
        "ranked_cells": len(ranked_list),
        "top_cells": len(top),
        "measurable_acceleration_cells": len(measurable),
        "accelerating_cells": sum(
            record.signal == "accelerating"
            for record in ranked_list
        ),
        "stable_cells": sum(
            record.signal == "stable"
            for record in ranked_list
        ),
        "decelerating_cells": sum(
            record.signal == "decelerating"
            for record in ranked_list
        ),
        "note": (
            "This is a GHSL historical built-up acceleration shortlist, "
            "not an investment ranking."
        ),
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return FirstScanResult(
        scanned_cells=len(ranked_list),
        ranked_cells=len(ranked_list),
        top_cells=len(top),
        measurable_acceleration_cells=len(measurable),
        accelerating_cells=int(summary["accelerating_cells"]),
        stable_cells=int(summary["stable_cells"]),
        decelerating_cells=int(summary["decelerating_cells"]),
        output_csv=str(csv_path),
        output_geojson=str(geojson_path),
        output_summary_json=str(summary_path),
    )


def run_first_real_scan(
    *,
    ghsl_dir: str | Path = "data/raw/ghsl",
    output_dir: str | Path = "data/output/first_scan",
    cell_km: float = 5.0,
    pool_size: int = 500,
    top_n: int = 100,
) -> FirstScanResult:
    if pool_size <= 0:
        raise ValueError("pool_size must be positive")
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    if top_n > pool_size:
        raise ValueError("top_n cannot exceed pool_size")

    readiness = check_data_readiness(
        ghsl_dir=ghsl_dir,
        ghsl_epochs=(2010, 2015, 2020),
    )
    if not readiness.required_ready:
        details = "; ".join(
            item.detail
            for item in readiness.items
            if item.required and item.status != "READY"
        )
        raise RuntimeError(
            "GHSL core is not ready for the first real scan: " + details
        )

    cells = build_pilot_grid(cell_km)
    effective_pool = min(pool_size, len(cells))
    scanned = scan_grid_ghsl(
        cells,
        ghsl_dir,
        limit=effective_pool,
    )
    ranked = rank_accelerating(scanned)

    return export_first_scan(
        ranked,
        top_n=min(top_n, len(ranked)),
        output_dir=output_dir,
    )

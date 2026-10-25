from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.config import resolve_cdse_credentials
from land_radar.grid import GridCell
from land_radar.providers.sentinel_surface import (
    SentinelSurfaceClient,
    SentinelSurfaceError,
)
from land_radar.sentinel_scan import scan_sentinel_change


def _parse_date(value: str | None, fallback: date) -> date:
    return date.fromisoformat(value) if value else fallback


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Compare two same-season Sentinel-2 windows for LAND RADAR "
            "Top-30 candidates and export raw spectral change evidence."
        )
    )
    p.add_argument(
        "--input",
        default="data/output/deep_scan/deep_scan_top30.csv",
    )
    p.add_argument(
        "--output-dir",
        default="data/output/sentinel_confirm",
    )
    p.add_argument("--cell-km", type=float, default=5.0)
    p.add_argument("--first-start")
    p.add_argument("--first-end")
    p.add_argument("--second-start")
    p.add_argument("--second-end")
    p.add_argument("--cloud", type=int, default=30)
    return p


def main() -> int:
    args = parser().parse_args()

    credentials = resolve_cdse_credentials()
    if credentials is None:
        print(
            "ERROR: CDSE_CLIENT_ID / CDSE_CLIENT_SECRET is required.",
            file=sys.stderr,
        )
        return 2

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Top-30 CSV not found: {input_path}", file=sys.stderr)
        return 2

    frame = pd.read_csv(input_path)
    required = {"cell_id", "center_lat", "center_lon"}
    missing = sorted(required - set(frame.columns))
    if missing:
        print(
            "ERROR: Top-30 CSV missing columns: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 2

    today = date.today()
    second_end = _parse_date(args.second_end, today)
    second_start = _parse_date(
        args.second_start,
        second_end - timedelta(days=60),
    )
    first_end = _parse_date(
        args.first_end,
        second_end - timedelta(days=365),
    )
    first_start = _parse_date(
        args.first_start,
        second_start - timedelta(days=365),
    )

    cells = [
        GridCell(
            cell_id=str(row.cell_id),
            center_lat=float(row.center_lat),
            center_lon=float(row.center_lon),
            size_km=float(args.cell_km),
        )
        for row in frame.itertuples(index=False)
    ]

    client = SentinelSurfaceClient(
        credentials.client_id,
        credentials.client_secret,
    )

    try:
        records = scan_sentinel_change(
            cells,
            client,
            first_start=first_start,
            first_end=first_end,
            second_start=second_start,
            second_end=second_end,
            max_cloud_coverage=int(args.cloud),
            cache_dir="data/cache/sentinel",
        )
    except (SentinelSurfaceError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    change_rows = []
    for record in records:
        change_rows.append(
            {
                "cell_id": record.cell_id,
                "center_lat": record.center_lat,
                "center_lon": record.center_lon,
                "first_start": record.first_start.isoformat(),
                "first_end": record.first_end.isoformat(),
                "second_start": record.second_start.isoformat(),
                "second_end": record.second_end.isoformat(),
                "first_ndvi": record.first_ndvi,
                "second_ndvi": record.second_ndvi,
                "delta_ndvi": record.delta_ndvi,
                "first_ndbi": record.first_ndbi,
                "second_ndbi": record.second_ndbi,
                "delta_ndbi": record.delta_ndbi,
                "first_bsi": record.first_bsi,
                "second_bsi": record.second_bsi,
                "delta_bsi": record.delta_bsi,
                "first_vegetation_share": record.first_vegetation_share,
                "second_vegetation_share": record.second_vegetation_share,
                "delta_vegetation_share_pp": record.delta_vegetation_share_pp,
                "first_bare_soil_share": record.first_bare_soil_share,
                "second_bare_soil_share": record.second_bare_soil_share,
                "delta_bare_soil_share_pp": record.delta_bare_soil_share_pp,
                "first_water_share": record.first_water_share,
                "second_water_share": record.second_water_share,
                "delta_water_share_pp": record.delta_water_share_pp,
                "first_valid_land_pixels": record.first_valid_land_pixels,
                "second_valid_land_pixels": record.second_valid_land_pixels,
                "cache_hit": record.cache_hit,
            }
        )

    change_df = pd.DataFrame(change_rows)
    change_csv = output_dir / "sentinel_top30_change.csv"
    merged_csv = output_dir / "top30_with_sentinel.csv"
    summary_json = output_dir / "sentinel_summary.json"

    change_df.to_csv(change_csv, index=False, encoding="utf-8-sig")
    merged = frame.merge(
        change_df,
        on=["cell_id", "center_lat", "center_lon"],
        how="left",
    )
    merged.to_csv(merged_csv, index=False, encoding="utf-8-sig")

    summary = {
        "candidate_count": len(records),
        "first_window": [first_start.isoformat(), first_end.isoformat()],
        "second_window": [second_start.isoformat(), second_end.isoformat()],
        "max_cloud_coverage": int(args.cloud),
        "cache_hits": sum(record.cache_hit for record in records),
        "warning": (
            "NDVI/NDBI/BSI/SCL changes are spectral evidence only. "
            "They do not independently prove construction or investment value."
        ),
    }
    summary_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("LAND RADAR SENTINEL TOP-30 CONFIRMATION")
    print("=" * 64)
    print(f"Candidates:     {len(records)}")
    print(f"First window:   {first_start} -> {first_end}")
    print(f"Second window:  {second_start} -> {second_end}")
    print(f"Cache hits:     {summary['cache_hits']}")
    print()
    print(f"Change CSV:     {change_csv}")
    print(f"Merged CSV:     {merged_csv}")
    print(f"Summary:        {summary_json}")
    print()
    print(
        "No construction label was generated. Review raw spectral evidence "
        "together with GHSL, terrain, catalyst and risk layers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

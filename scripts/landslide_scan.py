from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.landslide_scan import run_landslide_scan
from land_radar.providers.mta_landslide import (
    MTALandslideConfigError,
    OGCWFSError,
    resolve_mta_landslide_config,
)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Query configured MTA/TUCBS landslide inventory WFS around "
            "LAND RADAR Top-30 candidates."
        )
    )
    p.add_argument(
        "--input",
        default="data/output/deep_scan/deep_scan_top30.csv",
    )
    p.add_argument(
        "--output-dir",
        default="data/output/landslide_scan",
    )
    p.add_argument("--cell-km", type=float, default=5.0)
    p.add_argument("--padding-km", type=float, default=5.0)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        config = resolve_mta_landslide_config()
    except MTALandslideConfigError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if config is None:
        print(
            "MTA landslide WFS is not configured. Set both "
            "MTA_LANDSLIDE_WFS_URL and MTA_LANDSLIDE_TYPENAME.",
            file=sys.stderr,
        )
        return 2

    try:
        result = run_landslide_scan(
            candidate_csv=args.input,
            output_dir=args.output_dir,
            config=config,
            cell_km=args.cell_km,
            padding_km=args.padding_km,
        )
    except (FileNotFoundError, ValueError, OGCWFSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("LAND RADAR MTA LANDSLIDE INVENTORY")
    print("=" * 64)
    print(f"Candidates:      {result.candidate_count}")
    print(f"Features:        {result.feature_count}")
    print(f"CSV:             {result.output_csv}")
    print(f"GeoJSON:         {result.output_geojson}")
    print(f"Summary:         {result.summary_json}")
    print()
    print(
        "Inventory proximity is evidence only; it is not a susceptibility "
        "class or parcel-level hard veto."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

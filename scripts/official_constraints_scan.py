from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.official_constraints_scan import (
    run_official_constraints_scan,
)
from land_radar.providers.arcgis_geojson import ArcGISGeoJSONError


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Query official Tarım ve Orman ArcGIS services for protected "
            "areas and USBS flood-risk polygons around LAND RADAR Top-30."
        )
    )
    p.add_argument(
        "--input",
        default="data/output/deep_scan/deep_scan_top30.csv",
    )
    p.add_argument(
        "--output-dir",
        default="data/output/official_constraints",
    )
    p.add_argument("--cell-km", type=float, default=5.0)
    p.add_argument("--padding-km", type=float, default=5.0)
    return p


def main() -> int:
    args = parser().parse_args()
    if not Path(args.input).exists():
        print(
            f"ERROR: Top-30 deep-scan CSV not found: {args.input}",
            file=sys.stderr,
        )
        return 2

    try:
        result = run_official_constraints_scan(
            deep_scan_csv=args.input,
            output_dir=args.output_dir,
            cell_km=args.cell_km,
            query_padding_km=args.padding_km,
        )
    except (ArcGISGeoJSONError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("LAND RADAR OFFICIAL CONSTRAINTS SCAN")
    print("=" * 64)
    print(f"Candidates:          {result.candidate_count}")
    print(f"Protected features:  {result.protected_features}")
    print(f"Flood features:      {result.flood_features}")
    print()
    print(f"Protected CSV:       {result.protected_csv}")
    print(f"Flood CSV:           {result.flood_csv}")
    print(f"Protected GeoJSON:   {result.protected_geojson}")
    print(f"Flood GeoJSON:       {result.flood_geojson}")
    print(f"Summary:             {result.summary_json}")
    print()
    print("e-Plan zoning is still a separate unchecked evidence channel.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

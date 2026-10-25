from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.first_scan import run_first_real_scan
from land_radar.providers.ghsl import GHSLProviderError


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Run LAND RADAR's first real GHSL pilot scan: broad historical "
            "built-up acceleration scan -> top candidate shortlist."
        )
    )
    p.add_argument("--ghsl-dir", default="data/raw/ghsl")
    p.add_argument("--output-dir", default="data/output/first_scan")
    p.add_argument("--cell-km", type=float, default=5.0)
    p.add_argument("--pool", type=int, default=500)
    p.add_argument("--top", type=int, default=100)
    return p


def main() -> int:
    args = parser().parse_args()

    try:
        result = run_first_real_scan(
            ghsl_dir=args.ghsl_dir,
            output_dir=args.output_dir,
            cell_km=args.cell_km,
            pool_size=args.pool,
            top_n=args.top,
        )
    except (RuntimeError, ValueError, GHSLProviderError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("LAND RADAR FIRST REAL SCAN")
    print("=" * 64)
    print(f"Scanned cells:                 {result.scanned_cells}")
    print(f"Measurable acceleration cells: {result.measurable_acceleration_cells}")
    print(f"Accelerating:                  {result.accelerating_cells}")
    print(f"Stable:                        {result.stable_cells}")
    print(f"Decelerating:                  {result.decelerating_cells}")
    print(f"Top shortlist:                 {result.top_cells}")
    print()
    print(f"CSV:      {result.output_csv}")
    print(f"GeoJSON:  {result.output_geojson}")
    print(f"Summary:  {result.output_summary_json}")
    print()
    print(
        "Important: this is a GHSL historical acceleration shortlist, "
        "not an investment ranking."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

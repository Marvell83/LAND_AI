from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.kgm_highway_scan import run_kgm_highway_scan
from land_radar.providers.kgm_highway import KGMHighwayProviderError


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Fetch official KGM highway-project status evidence and link it "
            "to Top-30 cells only where a matching verified geometry exists."
        )
    )
    p.add_argument(
        "--input",
        default="data/output/deep_scan/deep_scan_top30.csv",
    )
    p.add_argument(
        "--geometry-registry",
        default="data/processed/geometry_registry.geojson",
    )
    p.add_argument(
        "--output-dir",
        default="data/output/kgm_highway_scan",
    )
    p.add_argument("--cell-km", type=float, default=5.0)
    p.add_argument("--max-distance-km", type=float, default=30.0)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        result = run_kgm_highway_scan(
            candidate_csv=args.input,
            geometry_registry_path=args.geometry_registry,
            output_dir=args.output_dir,
            cell_km=args.cell_km,
            max_distance_km=args.max_distance_km,
        )
    except (FileNotFoundError, ValueError, KGMHighwayProviderError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("LAND RADAR KGM HIGHWAY CATALYST SCAN")
    print("=" * 64)
    print(f"Candidates:             {result.candidate_count}")
    print(f"KGM projects:           {result.project_count}")
    print(f"Projects with geometry: {result.geometry_project_count}")
    print(f"Linked candidates:      {result.linked_candidate_count}")
    print()
    print(f"Projects CSV:           {result.projects_csv}")
    print(f"Links CSV:              {result.links_csv}")
    print(f"Top-30 CSV:             {result.candidate_csv}")
    print(f"Summary:                {result.summary_json}")
    print()
    print(
        "Project status is official KGM evidence; spatial distance is known "
        "only when a matching geometry-registry entry exists."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

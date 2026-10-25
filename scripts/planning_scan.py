from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.planning_scan import run_planning_scan


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Build point-in-time planning evidence for LAND RADAR Top-30 "
            "using verified TUCBS CDP WMS coverage and an optional plan registry."
        )
    )
    p.add_argument(
        "--candidates",
        default="data/output/deep_scan/deep_scan_top30.csv",
    )
    p.add_argument(
        "--plan-registry",
        default="data/processed/plan_registry.json",
    )
    p.add_argument(
        "--output-dir",
        default="data/output/planning_scan",
    )
    p.add_argument(
        "--as-of",
        default=date.today().isoformat(),
    )
    return p


def main() -> int:
    args = parser().parse_args()
    registry = Path(args.plan_registry)

    try:
        result = run_planning_scan(
            candidate_csv=args.candidates,
            plan_registry_path=(registry if registry.exists() else None),
            output_dir=args.output_dir,
            as_of_date=date.fromisoformat(args.as_of),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("LAND RADAR TOP-30 PLANNING EVIDENCE")
    print("=" * 64)
    print(f"Candidates:          {result.candidate_count}")
    print(f"CDP WMS covered:     {result.wms_covered_count}")
    print(f"Registry matches:    {result.registry_match_count}")
    print(f"Planning known:      {result.planning_known_count}")
    print()
    print(f"CSV:                 {result.output_csv}")
    print(f"Summary:             {result.summary_json}")
    print()
    print(
        "CDP WMS coverage alone is not parcel zoning. Verified finalized "
        "UIP/NIP evidence is required for planning_known."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

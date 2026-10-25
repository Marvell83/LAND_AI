from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.evidence_packet import build_evidence_packets


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Build per-cell LAND RADAR evidence packets from Top-30 deep-scan "
            "and optional Sentinel confirmation outputs."
        )
    )
    p.add_argument(
        "--deep-scan",
        default="data/output/deep_scan/deep_scan_top30.csv",
    )
    p.add_argument(
        "--sentinel",
        default="data/output/sentinel_confirm/sentinel_top30_change.csv",
    )
    p.add_argument(
        "--protected",
        default="data/output/official_constraints/protected_area_top30.csv",
    )
    p.add_argument(
        "--flood",
        default="data/output/official_constraints/flood_risk_top30.csv",
    )
    p.add_argument(
        "--landslide",
        default="data/output/landslide_scan/landslide_top30.csv",
    )
    p.add_argument(
        "--price",
        default="data/output/price_scan/price_top30.csv",
    )
    p.add_argument(
        "--planning",
        default="data/output/planning_scan/planning_top30.csv",
    )
    p.add_argument(
        "--output-dir",
        default="data/output/evidence_packets",
    )
    return p


def main() -> int:
    args = parser().parse_args()
    sentinel = Path(args.sentinel)
    protected = Path(args.protected)
    flood = Path(args.flood)
    landslide = Path(args.landslide)
    price = Path(args.price)
    planning = Path(args.planning)
    sentinel_arg = sentinel if sentinel.exists() else None
    protected_arg = protected if protected.exists() else None
    flood_arg = flood if flood.exists() else None
    landslide_arg = landslide if landslide.exists() else None
    price_arg = price if price.exists() else None
    planning_arg = planning if planning.exists() else None

    try:
        result = build_evidence_packets(
            deep_scan_csv=args.deep_scan,
            sentinel_csv=sentinel_arg,
            protected_csv=protected_arg,
            flood_csv=flood_arg,
            landslide_csv=landslide_arg,
            price_csv=price_arg,
            planning_csv=planning_arg,
            output_dir=args.output_dir,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("LAND RADAR EVIDENCE PACKETS")
    print("=" * 64)
    print(f"Candidates:   {result.candidate_count}")
    print(f"Master JSON:  {result.output_master_json}")
    print(f"Matrix CSV:   {result.output_matrix_csv}")
    print(f"Cell packets: {result.output_packet_dir}")
    print()
    print("Evidence coverage is completeness only; it is not an investment score.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.candidate_price_scan import run_candidate_price_scan
from land_radar.inflation import InflationDataError
from land_radar.pricing import PriceDataError


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Build local comparable-price evidence for LAND RADAR Top-30 "
            "candidate cells."
        )
    )
    p.add_argument(
        "--candidates",
        default="data/output/deep_scan/deep_scan_top30.csv",
    )
    p.add_argument("--comparables", required=True)
    p.add_argument(
        "--output-dir",
        default="data/output/price_scan",
    )
    p.add_argument(
        "--as-of",
        default=date.today().isoformat(),
        help="Analysis cutoff date YYYY-MM-DD.",
    )
    p.add_argument("--radius-km", type=float, default=10.0)
    p.add_argument("--max-age-days", type=int, default=730)
    p.add_argument("--land-type")
    p.add_argument("--cpi")
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        result = run_candidate_price_scan(
            candidate_csv=args.candidates,
            comparable_csv=args.comparables,
            output_dir=args.output_dir,
            as_of_date=date.fromisoformat(args.as_of),
            radius_km=args.radius_km,
            max_age_days=args.max_age_days,
            land_type=args.land_type,
            cpi_csv=args.cpi,
        )
    except (
        FileNotFoundError,
        ValueError,
        PriceDataError,
        InflationDataError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("LAND RADAR TOP-30 PRICE EVIDENCE")
    print("=" * 64)
    print(f"Candidates:       {result.candidate_count}")
    print(f"Known price:      {result.known_count}")
    print(f"Low confidence:   {result.low_confidence_count}")
    print(f"No comparables:   {result.no_comparable_count}")
    print()
    print(f"CSV:              {result.output_csv}")
    print(f"Summary:          {result.summary_json}")
    print()
    print(
        "Known price means MEDIUM/HIGH comparable-data confidence only; "
        "it is not a parcel valuation."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

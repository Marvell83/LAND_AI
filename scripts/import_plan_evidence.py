from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.plan_import import PlanImportError, import_plan_csv


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Import dated official e-Plan / municipal plan evidence from CSV "
            "into LAND RADAR's point-in-time plan registry."
        )
    )
    p.add_argument("--csv", required=True)
    p.add_argument(
        "--output",
        default="data/processed/plan_registry.json",
    )
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        plans = import_plan_csv(args.csv, args.output)
    except (FileNotFoundError, PlanImportError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("LAND RADAR PLAN EVIDENCE IMPORT")
    print("=" * 64)
    print(f"Imported plans: {len(plans)}")
    print(f"Registry:       {args.output}")
    for plan in plans[:20]:
        print(
            f"  {plan.plan_id:20} {plan.plan_type:4} "
            f"{plan.stage.name:16} geometry={plan.geometry_verified}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

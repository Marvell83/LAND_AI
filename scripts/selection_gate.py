from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.selection_gate import run_selection_gate


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Check whether LAND RADAR Top-30 candidates have enough evidence "
            "to begin a Top-10 review. No opportunity ranking is produced."
        )
    )
    p.add_argument(
        "--evidence",
        default="data/output/evidence_packets/candidate_evidence_packets.json",
    )
    p.add_argument(
        "--output-dir",
        default="data/output/selection_gate",
    )
    p.add_argument("--target", type=int, default=10)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        result = run_selection_gate(
            evidence_json=args.evidence,
            output_dir=args.output_dir,
            target_count=args.target,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("LAND RADAR 30 -> 10 EVIDENCE GATE")
    print("=" * 64)
    print(f"Candidates:       {result.candidate_count}")
    print(f"Eligible:         {result.eligible_count}")
    print(f"Target:           {result.target_count}")
    print(
        "Selection ready: "
        + ("YES" if result.selection_ready else "NO")
    )
    print()
    print(f"CSV:              {result.output_csv}")
    print(f"Summary:          {result.summary_json}")
    print()
    if not result.selection_ready:
        print(
            "Top-10 narrowing is blocked until enough candidates have all "
            "required evidence layers."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

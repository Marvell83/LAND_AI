from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.geometry_import import (
    GeometryImportError,
    append_registry_entries,
    load_raw_geometry_file,
    make_registry_entries,
)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Import a verified raw GeoJSON/KML route or boundary into "
            "LAND RADAR Geometry Registry with explicit provenance."
        )
    )
    p.add_argument("--input", required=True)
    p.add_argument("--catalyst-id", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--source-url", required=True)
    p.add_argument(
        "--role",
        required=True,
        choices=[
            "official_vector_route",
            "digitized_official_map",
            "schematic_route",
            "official_boundary",
            "observed_geometry",
        ],
    )
    p.add_argument("--confidence", type=float, required=True)
    p.add_argument(
        "--observed-date",
        default=date.today().isoformat(),
    )
    p.add_argument(
        "--manual-verified",
        action="store_true",
    )
    p.add_argument(
        "--registry",
        default="data/processed/geometry_registry.geojson",
    )
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        raw = load_raw_geometry_file(args.input)
        entries = make_registry_entries(
            raw,
            catalyst_id=args.catalyst_id,
            source=args.source,
            source_url=args.source_url,
            observed_date=date.fromisoformat(args.observed_date),
            confidence=args.confidence,
            geometry_role=args.role,
            manual_verified=args.manual_verified,
        )
        combined = append_registry_entries(
            args.registry,
            entries,
        )
    except (
        FileNotFoundError,
        GeometryImportError,
        ValueError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("LAND RADAR GEOMETRY EVIDENCE IMPORT")
    print("=" * 64)
    print(f"Imported features: {len(entries)}")
    print(f"Registry entries:  {len(combined)}")
    print(f"Registry:          {args.registry}")
    print()
    for entry in entries:
        print(
            f"  {entry.catalyst_id} | {entry.evidence.geometry_role} | "
            f"{entry.evidence.feature_name} | confidence={entry.evidence.confidence}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

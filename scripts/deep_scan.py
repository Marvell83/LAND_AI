from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.catalyst import Catalyst
from land_radar.config import resolve_cdse_credentials
from land_radar.deep_scan import run_deep_scan
from land_radar.providers.aygm_rail import (
    AYGMRailProviderError,
    fetch_rail_projects,
    record_to_catalyst as rail_record_to_catalyst,
)
from land_radar.providers.copernicus_dem import CopernicusProcessClient
from land_radar.providers.kgm_highway import (
    KGMHighwayProviderError,
    fetch_highway_projects,
    record_to_catalyst as highway_record_to_catalyst,
)
from land_radar.providers.osbuk import (
    OSBUKProviderError,
    fetch_osb_list,
    filter_provinces,
    record_to_catalyst,
)


PILOT_PROVINCES = ["Sakarya", "Bursa", "Balıkesir", "Çanakkale"]


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Deepen LAND RADAR's first GHSL shortlist using terrain, hazard "
            "and verified catalyst geometry where available."
        )
    )
    p.add_argument(
        "--input",
        default="data/output/first_scan/ghsl_top_candidates.csv",
    )
    p.add_argument(
        "--output-dir",
        default="data/output/deep_scan",
    )
    p.add_argument("--cell-km", type=float, default=5.0)
    p.add_argument("--top", type=int, default=30)
    p.add_argument("--max-p90-slope", type=float, default=12.0)
    p.add_argument("--max-catalyst-km", type=float, default=20.0)
    p.add_argument(
        "--require-catalyst",
        action="store_true",
        help="Drop cells without a verified catalyst geometry within range.",
    )
    p.add_argument(
        "--no-dem",
        action="store_true",
        help="Do not call Copernicus DEM even if OAuth credentials exist.",
    )
    return p


def _load_live_catalysts() -> tuple[dict[str, Catalyst], list[str]]:
    catalysts: dict[str, Catalyst] = {}
    notes: list[str] = []

    try:
        records = filter_provinces(
            fetch_osb_list(),
            PILOT_PROVINCES,
        )
        for record in records:
            catalyst = record_to_catalyst(record)
            catalysts[catalyst.catalyst_id] = catalyst
    except OSBUKProviderError as exc:
        notes.append(f"osbuk_unavailable:{exc}")

    try:
        for record in fetch_rail_projects():
            catalyst = rail_record_to_catalyst(record)
            catalysts[catalyst.catalyst_id] = catalyst
    except AYGMRailProviderError as exc:
        notes.append(f"aygm_unavailable:{exc}")

    try:
        for record in fetch_highway_projects():
            catalyst = highway_record_to_catalyst(record)
            catalysts[catalyst.catalyst_id] = catalyst
    except KGMHighwayProviderError as exc:
        notes.append(f"kgm_highway_unavailable:{exc}")

    return catalysts, notes


def main() -> int:
    args = parser().parse_args()

    credentials = resolve_cdse_credentials()
    terrain_client = None
    if credentials is not None and not args.no_dem:
        terrain_client = CopernicusProcessClient(
            credentials.client_id,
            credentials.client_secret,
        )

    geometry_path = Path("data/processed/geometry_registry.geojson")
    catalysts: dict[str, Catalyst] = {}
    network_notes: list[str] = []
    if geometry_path.exists():
        catalysts, network_notes = _load_live_catalysts()

    try:
        result = run_deep_scan(
            first_scan_csv=args.input,
            output_dir=args.output_dir,
            cell_km=args.cell_km,
            final_top_n=args.top,
            terrain_client=terrain_client,
            hazard_registry_path="data/processed/hazard_registry.geojson",
            geometry_registry_path=geometry_path,
            catalysts=catalysts,
            max_p90_slope_deg=args.max_p90_slope,
            max_catalyst_distance_km=args.max_catalyst_km,
            require_catalyst=args.require_catalyst,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("LAND RADAR DEEP SCAN 100 -> 30")
    print("=" * 64)
    print(f"Input candidates:    {result.input_candidates}")
    print(f"PASS:                {result.pass_count}")
    print(f"PASS_WITH_GAPS:      {result.pass_with_gaps_count}")
    print(f"DROP:                {result.drop_count}")
    print(f"Finalists:           {result.finalists}")
    print()
    print(f"Full CSV:            {result.output_full_csv}")
    print(f"Top CSV:             {result.output_final_csv}")
    print(f"Top GeoJSON:         {result.output_final_geojson}")
    print(f"Summary:             {result.output_summary_json}")

    all_notes = list(result.notes) + network_notes
    if all_notes:
        print()
        print("Data gaps / notes:")
        for note in all_notes:
            print(f"  - {note}")

    if terrain_client is None:
        print()
        print(
            "DEM not used: configure CDSE OAuth or keep terrain as explicit unknown."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

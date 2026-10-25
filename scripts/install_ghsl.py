from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.ghsl_install import GHSLInstallError, install_sources
from land_radar.readiness import check_data_readiness


OFFICIAL_DOWNLOAD_PAGE = (
    "https://human-settlement.emergency.copernicus.eu/download.php?ds=bu"
)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Install official GHS-BUILT-S R2023A 100m GeoTIFFs for LAND RADAR. "
            "Use manually downloaded GHSL ZIP files or official EU ZIP URLs."
        )
    )
    p.add_argument(
        "--zip",
        dest="zip_paths",
        action="append",
        default=[],
        help="Path to an official GHSL ZIP. Repeat for multiple files.",
    )
    p.add_argument(
        "--url",
        dest="urls",
        action="append",
        default=[],
        help="Official europa.eu / ec.europa.eu GHSL ZIP URL. Repeat as needed.",
    )
    p.add_argument(
        "--destination",
        default="data/raw/ghsl",
        help="Destination directory for extracted GeoTIFFs.",
    )
    p.add_argument(
        "--epochs",
        nargs="+",
        type=int,
        default=[2010, 2015, 2020],
        help="Epochs to extract. Default: 2010 2015 2020",
    )
    return p


def main() -> int:
    args = parser().parse_args()

    if not args.zip_paths and not args.urls:
        print("No GHSL ZIP or URL supplied.")
        print("Official download page:")
        print(OFFICIAL_DOWNLOAD_PAGE)
        print()
        print("Example after downloading ZIP files in your browser:")
        print(
            "python scripts/install_ghsl.py "
            "--zip C:\\Users\\YOU\\Downloads\\ghsl_tile.zip"
        )
        return 2

    try:
        installed = install_sources(
            zip_paths=args.zip_paths,
            urls=args.urls,
            destination_dir=args.destination,
            epochs=args.epochs,
        )
    except GHSLInstallError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print("Installed / validated GHSL rasters:")
    for item in installed:
        print(
            f"  E{item.epoch}  {item.crs}  {item.dtype:6}  "
            f"{item.width}x{item.height}  {item.destination}"
        )

    report = check_data_readiness(
        ghsl_dir=args.destination,
        ghsl_epochs=args.epochs,
    )
    print()
    for item in report.items:
        if item.key.startswith("ghsl_"):
            print(f"{item.status:10} {item.key:12} {item.detail}")

    return 0 if report.required_ready else 3


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from land_radar.config import resolve_cdse_credentials
from land_radar.readiness import check_data_readiness


def main() -> int:
    credentials = resolve_cdse_credentials()
    report = check_data_readiness(
        cdse_credentials_available=credentials is not None,
    )

    print("LAND RADAR DATA READINESS")
    print("=" * 60)
    for item in report.items:
        required = "required" if item.required else "optional"
        print(f"{item.status:16} {required:8} {item.key:20} {item.detail}")

    print("=" * 60)
    print(
        "Required core ready:"
        f" {'YES' if report.required_ready else 'NO'}"
    )
    return 0 if report.required_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ -z "${MTA_LANDSLIDE_WFS_URL:-}" || -z "${MTA_LANDSLIDE_TYPENAME:-}" ]]; then
  echo "MTA/TUCBS WFS yapılandırması eksik."
  echo
  echo "Codespaces secrets/environment variables:"
  echo "  MTA_LANDSLIDE_WFS_URL"
  echo "  MTA_LANDSLIDE_TYPENAME"
  echo
  echo "Uç nokta/typeName doğrulanmadan LAND RADAR bunları tahmin etmez."
  exit 2
fi

if [[ ! -f "data/output/deep_scan/deep_scan_top30.csv" ]]; then
  echo "Top-30 deep scan dosyası bulunamadı."
  exit 2
fi

python -m pip install --disable-pip-version-check -r requirements.txt

echo "=== LAND RADAR MTA/TUCBS HEYELAN ENVANTERİ ==="
python scripts/landslide_scan.py

echo
echo "Çıktılar:"
echo "  data/output/landslide_scan/landslide_top30.csv"
echo "  data/output/landslide_scan/landslide_features.geojson"
echo "  data/output/landslide_scan/landslide_scan_summary.json"
echo
echo "Evidence Packet'i yenile:"
echo "  python scripts/build_evidence_packets.py"

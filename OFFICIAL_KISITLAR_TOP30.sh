#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f "data/output/deep_scan/deep_scan_top30.csv" ]]; then
  echo "Top-30 deep scan dosyası bulunamadı."
  echo "Önce: python scripts/deep_scan.py --top 30"
  exit 2
fi

python -m pip install --disable-pip-version-check -r requirements.txt

echo "=== LAND RADAR RESMİ KISIT / TAŞKIN TARAMASI ==="
python scripts/official_constraints_scan.py

echo
echo "Çıktılar:"
echo "  data/output/official_constraints/protected_area_top30.csv"
echo "  data/output/official_constraints/flood_risk_top30.csv"
echo "  data/output/official_constraints/protected_area_features.geojson"
echo "  data/output/official_constraints/flood_risk_features.geojson"
echo
echo "Evidence Packet'i yenilemek için:"
echo "  python scripts/build_evidence_packets.py"

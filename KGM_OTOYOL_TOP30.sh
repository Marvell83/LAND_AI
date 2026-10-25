#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f "data/output/deep_scan/deep_scan_top30.csv" ]]; then
  echo "Top-30 deep scan dosyası bulunamadı."
  echo "Önce: python scripts/deep_scan.py --top 30"
  exit 2
fi

python -m pip install --disable-pip-version-check -r requirements.txt

echo "=== LAND RADAR KGM OTOYOL KATALİZÖR TARAMASI ==="
python scripts/kgm_highway_scan.py

echo
echo "Çıktılar:"
echo "  data/output/kgm_highway_scan/kgm_highway_projects.csv"
echo "  data/output/kgm_highway_scan/kgm_highway_links.csv"
echo "  data/output/kgm_highway_scan/kgm_highway_top30.csv"
echo "  data/output/kgm_highway_scan/kgm_highway_scan_summary.json"
echo
echo "Not: KGM statüsü resmîdir; mesafe yalnız eşleşen Geometry Registry"
echo "güzergâhı varsa hesaplanır."
echo
echo "Evidence Packet'i yenile:"
echo "  python scripts/build_evidence_packets.py"

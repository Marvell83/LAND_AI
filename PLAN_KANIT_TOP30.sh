#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f "data/output/deep_scan/deep_scan_top30.csv" ]]; then
  echo "Top-30 deep scan dosyası bulunamadı."
  echo "Önce: python scripts/deep_scan.py --top 30"
  exit 2
fi

python -m pip install --disable-pip-version-check -r requirements.txt

echo "=== LAND RADAR TOP-30 PLANNING EVIDENCE ==="
python scripts/planning_scan.py

echo
echo "Çıktılar:"
echo "  data/output/planning_scan/planning_top30.csv"
echo "  data/output/planning_scan/planning_scan_summary.json"
echo
echo "Resmî plan CSV'niz varsa önce registry üretin:"
echo "  python scripts/import_plan_evidence.py --csv data/processed/plans.csv"
echo
echo "Ardından planning scan'i tekrar çalıştırın ve Evidence Packet'i yenileyin:"
echo "  python scripts/planning_scan.py"
echo "  python scripts/build_evidence_packets.py"
echo "  bash TOP10_GATE.sh"

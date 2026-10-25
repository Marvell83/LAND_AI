#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ $# -lt 1 ]]; then
  echo "Kullanım:"
  echo "  bash PRICE_TOP30.sh data/processed/comparables.csv"
  echo
  echo "Opsiyonel CPI kullanımı:"
  echo "  python scripts/candidate_price_scan.py --comparables data/processed/comparables.csv --cpi data/processed/cpi.csv"
  exit 2
fi

COMPARABLES="$1"

if [[ ! -f "$COMPARABLES" ]]; then
  echo "Emsal CSV bulunamadı: $COMPARABLES"
  exit 2
fi

if [[ ! -f "data/output/deep_scan/deep_scan_top30.csv" ]]; then
  echo "Top-30 deep scan dosyası bulunamadı."
  echo "Önce: python scripts/deep_scan.py --top 30"
  exit 2
fi

python -m pip install --disable-pip-version-check -r requirements.txt

echo "=== LAND RADAR TOP-30 PRICE EVIDENCE ==="
python scripts/candidate_price_scan.py   --comparables "$COMPARABLES"   --radius-km 10   --max-age-days 730

echo
echo "Çıktılar:"
echo "  data/output/price_scan/price_top30.csv"
echo "  data/output/price_scan/price_scan_summary.json"
echo
echo "Evidence Packet'i yenilemek için:"
echo "  python scripts/build_evidence_packets.py"

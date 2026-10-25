#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f "data/output/evidence_packets/candidate_evidence_packets.json" ]]; then
  echo "Evidence Packet bulunamadı."
  echo "Önce: python scripts/build_evidence_packets.py"
  exit 2
fi

python -m pip install --disable-pip-version-check -r requirements.txt

echo "=== LAND RADAR 30 -> 10 EVIDENCE GATE ==="
python scripts/selection_gate.py --target 10

echo
echo "Çıktılar:"
echo "  data/output/selection_gate/selection_gate.csv"
echo "  data/output/selection_gate/selection_gate_summary.json"

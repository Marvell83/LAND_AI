#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ $# -lt 5 ]]; then
  echo "Kullanım:"
  echo "  bash GEOMETRI_KANIT_IMPORT.sh <dosya.kml|geojson> <catalyst_id> <source> <https_source_url> <role> [confidence]"
  echo
  echo "Roller:"
  echo "  official_vector_route"
  echo "  digitized_official_map"
  echo "  schematic_route"
  echo "  official_boundary"
  echo "  observed_geometry"
  exit 2
fi

INPUT="$1"
CATALYST_ID="$2"
SOURCE="$3"
SOURCE_URL="$4"
ROLE="$5"
CONFIDENCE="${6:-90}"

EXTRA=()
if [[ "$ROLE" == "digitized_official_map" || "$ROLE" == "schematic_route" ]]; then
  EXTRA+=(--manual-verified)
fi

python -m pip install --disable-pip-version-check -r requirements.txt

python scripts/import_geometry_evidence.py   --input "$INPUT"   --catalyst-id "$CATALYST_ID"   --source "$SOURCE"   --source-url "$SOURCE_URL"   --role "$ROLE"   --confidence "$CONFIDENCE"   "${EXTRA[@]}"

echo
echo "Registry güncellendi:"
echo "  data/processed/geometry_registry.geojson"

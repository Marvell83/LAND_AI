#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "[LAND RADAR] Python:"
python --version

echo "[LAND RADAR] Bağımlılıklar kontrol ediliyor..."
python -m pip install --disable-pip-version-check -r requirements.txt

echo "[LAND RADAR] Streamlit 8501 portunda başlatılıyor..."
echo "Codespaces PORTS sekmesinde 8501 / LAND RADAR Streamlit bağlantısını açın."

exec python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true

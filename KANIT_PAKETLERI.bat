@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error

python -m pip install -r requirements.txt
if errorlevel 1 goto :error

if not exist "data\output\deep_scan\deep_scan_top30.csv" (
    echo.
    echo Top-30 deep scan dosyasi bulunamadi.
    echo Once DERIN_TARAMA_100_30.bat calistirin.
    echo.
    pause
    exit /b 2
)

echo.
echo === LAND RADAR EVIDENCE PACKETS ===
python scripts\build_evidence_packets.py
if errorlevel 1 goto :error

echo.
echo Sonuclar:
echo   data\output\evidence_packets\candidate_evidence_matrix.csv
echo   data\output\evidence_packets\candidate_evidence_packets.json
echo   data\output\evidence_packets\cells\
echo.
pause
exit /b 0

:error
echo.
echo Evidence Packet uretimi basarisiz.
pause
exit /b 1

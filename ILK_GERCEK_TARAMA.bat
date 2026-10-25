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

echo.
echo === DATA READINESS ===
python scripts\check_readiness.py
if errorlevel 1 (
    echo.
    echo Zorunlu GHSL verisi hazir degil. Once GHSL_ZIP_KUR.bat ile
    echo 2010, 2015 ve 2020 resmi R2023A 100m verilerini kurun.
    pause
    exit /b 2
)

echo.
echo === 500 -^> 100 GHSL TARAMASI ===
python scripts\first_real_scan.py --cell-km 5 --pool 500 --top 100
if errorlevel 1 goto :error

echo.
echo Sonuclar:
echo   data\output\first_scan\ghsl_top_candidates.csv
echo   data\output\first_scan\ghsl_top_candidates.geojson
echo   data\output\first_scan\ghsl_scan_summary.json
echo.
pause
exit /b 0

:error
echo.
echo Ilk gercek tarama basarisiz.
pause
exit /b 1

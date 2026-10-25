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

if not exist "data\output\first_scan\ghsl_top_candidates.csv" (
    echo.
    echo Ilk tarama CSV bulunamadi.
    echo Once ILK_GERCEK_TARAMA.bat calistirin.
    echo.
    pause
    exit /b 2
)

echo.
echo === LAND RADAR 100 -^> 30 DERIN TARAMA ===
python scripts\deep_scan.py --top 30 --cell-km 5 --max-p90-slope 12 --max-catalyst-km 20
if errorlevel 1 goto :error

echo.
echo Sonuclar:
echo   data\output\deep_scan\deep_scan_all_candidates.csv
echo   data\output\deep_scan\deep_scan_top30.csv
echo   data\output\deep_scan\deep_scan_top30.geojson
echo   data\output\deep_scan\deep_scan_summary.json
echo.
pause
exit /b 0

:error
echo.
echo Derin tarama basarisiz.
pause
exit /b 1

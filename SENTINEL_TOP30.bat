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
    echo Top-30 dosyasi bulunamadi.
    echo Once DERIN_TARAMA_100_30.bat calistirin.
    echo.
    pause
    exit /b 2
)

echo.
echo === SENTINEL TOP-30 IKI DONEM KARSILASTIRMA ===
python scripts\sentinel_confirm.py
if errorlevel 1 goto :error

echo.
echo Sonuclar:
echo   data\output\sentinel_confirm\sentinel_top30_change.csv
echo   data\output\sentinel_confirm\top30_with_sentinel.csv
echo   data\output\sentinel_confirm\sentinel_summary.json
echo.
pause
exit /b 0

:error
echo.
echo Sentinel Top-30 taramasi basarisiz.
echo CDSE OAuth bilgilerinin .streamlit\secrets.toml veya ortam degiskenlerinde
echo tanimli oldugunu kontrol edin.
pause
exit /b 1

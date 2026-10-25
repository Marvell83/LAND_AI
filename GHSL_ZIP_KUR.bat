@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" (
    echo.
    echo Kullanim:
    echo   GHSL_ZIP_KUR.bat "C:\Yol\ghsl_dosyasi.zip"
    echo.
    echo Resmi GHSL ZIP dosyasini bu BAT dosyasinin ustune surukleyip
    echo birakmaniz da yeterlidir.
    echo.
    pause
    exit /b 2
)

if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error

python -m pip install -r requirements.txt
if errorlevel 1 goto :error

python scripts\install_ghsl.py --zip "%~1"
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" (
    echo GHSL zorunlu epoch dosyalari hazir.
) else (
    echo ZIP islendi. Tum 2010 / 2015 / 2020 epoch dosyalari henuz tamamlanmamis olabilir.
    echo Diger resmi GHSL ZIP dosyalarini da ayni sekilde kurun.
)
echo.
python scripts\check_readiness.py
pause
exit /b %RC%

:error
echo.
echo GHSL kurulumu basarisiz.
pause
exit /b 1

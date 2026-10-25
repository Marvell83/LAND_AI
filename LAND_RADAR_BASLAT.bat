@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [LAND RADAR] Sanal ortam bulunamadi. Kurulum yapiliyor...
    py -3.12 -m venv .venv
    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error

python -m pip install -r requirements.txt
if errorlevel 1 goto :error

python -m streamlit run app.py
goto :eof

:error
echo.
echo LAND RADAR baslatilamadi. Yukaridaki hata mesajini kontrol edin.
pause
exit /b 1

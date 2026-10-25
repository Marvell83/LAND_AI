@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [LAND RADAR] Sanal ortam bulunamadi. Kurulum yapiliyor...

    where py >nul 2>nul
    if not errorlevel 1 (
        py -3.12 -c "import sys" >nul 2>nul
        if not errorlevel 1 (
            py -3.12 -m venv .venv
        ) else (
            py -3 -m venv .venv
        )
    ) else (
        where python >nul 2>nul
        if errorlevel 1 goto :python_missing
        python -m venv .venv
    )

    if errorlevel 1 goto :error
)

call ".venv\Scripts\activate.bat"
if errorlevel 1 goto :error

python -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :error

echo.
echo [LAND RADAR] Baslatiliyor...
echo Tarayiciniz otomatik acilmazsa terminalde gorunen Local URL adresini acin.
echo.

python -m streamlit run app.py
goto :eof

:python_missing
echo.
echo Python bulunamadi.
echo Python 3.12 kurulumu yapip bu dosyayi tekrar calistirin.
pause
exit /b 2

:error
echo.
echo LAND RADAR baslatilamadi. Yukaridaki hata mesajini kontrol edin.
pause
exit /b 1

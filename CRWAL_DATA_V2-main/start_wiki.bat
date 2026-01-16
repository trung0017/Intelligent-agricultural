@echo off
echo ========================================
echo       WIKINONGSAN - KHOI DONG
echo ========================================
echo.

echo Kiem tra Python...
python --version
if errorlevel 1 (
    echo Loi: Python chua duoc cai dat!
    echo Vui long cai Python tu https://python.org
    pause
    exit /b 1
)

echo.
echo Kiem tra cac thu vien...
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Cai dat cac thu vien...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Loi cai dat thu vien!
        pause
        exit /b 1
    )
)

echo.
echo Tao thu muc can thiet...
if not exist "pages" mkdir pages
if not exist "static" mkdir static
if not exist "templates" mkdir templates
if not exist "raw_content" mkdir raw_content
if not exist "cleaned_content" mkdir cleaned_content

echo.
echo Khoi dong WikiNongSan...
echo Truy cap: http://localhost:8000
echo Nhan Ctrl+C de dung lai
echo.

python app.py

pause
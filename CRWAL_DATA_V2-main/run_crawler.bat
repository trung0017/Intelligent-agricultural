@echo off
echo ========================================
echo      WIKINONGSAN - CRAWLER
echo ========================================
echo.

echo Thu thap noi dung tu cac trang web va tong hop thanh bai viet wiki
echo.

echo Kiem tra Python...
python --version
if errorlevel 1 (
    echo Loi: Python chua duoc cai dat!
    pause
    exit /b 1
)

echo.
echo Kiem tra Ollama (tuy chon)...
curl -s http://127.0.0.1:11500/api/tags >nul 2>&1
if errorlevel 1 (
    echo Canh bao: Ollama chua chay tren port 11500
    echo De co ket qua tot nhat, hay chay:
    echo   set OLLAMA_HOST=127.0.0.1:11500
    echo   ollama serve
    echo.
    echo Nhan Enter de tiep tuc voi che do co ban...
    pause
) else (
    echo Ollama da san sang tren port 11500
)

echo.
echo Khoi dong WikiNongSan Crawler...
echo.

python crawler.py

echo.
echo Hoan thanh! Nhan phim bat ky de dong...
pause
@echo off
echo ========================================
echo    KHOI DONG OLLAMA VOI PORT TUY CHINH
echo ========================================
echo.

echo Thiet lap port Ollama: 127.0.0.1:11500
set OLLAMA_HOST=127.0.0.1:11500

echo.
echo Kiem tra Ollama da cai chua...
ollama --version
if errorlevel 1 (
    echo Loi: Ollama chua duoc cai dat!
    echo Vui long tai tu: https://ollama.ai/download
    pause
    exit /b 1
)

echo.
echo Kiem tra model AI...
ollama list | findstr qwen2.5:7b
if errorlevel 1 (
    echo Chua co model qwen2.5:7b
    echo Dang tai model... (co the mat vai phut)
    ollama pull qwen2.5:7b
    if errorlevel 1 (
        echo Loi tai model!
        pause
        exit /b 1
    )
)

echo.
echo Khoi dong Ollama tren port 11500...
echo URL: http://127.0.0.1:11500
echo Nhan Ctrl+C de dung lai
echo.
echo Sau khi khoi dong, chay:
echo - python crawler.py (de thu thap noi dung)
echo - python app.py (de khoi dong website)
echo.
echo Chi tiet xem file SETUP.md
echo.

ollama serve
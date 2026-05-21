@echo off
chcp 65001 >nul
echo [啟動] FastAPI Server - http://localhost:8000
echo [文件] API 互動介面 - http://localhost:8000/docs
echo.
python3.12 -m uvicorn main:app --reload --port 8000
pause

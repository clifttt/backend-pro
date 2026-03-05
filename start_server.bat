@echo off
REM Скрипт для запуска FastAPI сервера

cd /d "D:\Downloads\backend-pro-main\backend-pro-main"

echo Current directory: %cd%
echo.
echo Запускаем FastAPI сервер...
echo.

python -m uvicorn app.main:app --reload --port 8000

pause

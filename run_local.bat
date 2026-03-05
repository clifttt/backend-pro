@echo off
REM Скрипт для запуска приложения локально (требует PostgreSQL)

echo 🚀 Investment Intelligence Hub - Local Launch
echo ============================================

REM Установка переменных окружения
set DATABASE_URL_LOCAL=postgresql+psycopg://postgres:postgres@localhost:5432/invest_db

REM Проверяем наличие Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python не найден. Пожалуйста, установите Python 3.10+
    exit /b 1
)

REM Проверяем наличие виртуального окружения
if not exist "venv" (
    echo 📦 Создание виртуального окружения...
    python -m venv venv
)

REM Активируем виртуальное окружение
echo 🔧 Активация виртуального окружения...
call venv\Scripts\activate.bat

REM Установим зависимости
echo 📥 Установка зависимостей...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Инициализируем БД
echo 💾 Инициализация БД...
python init_db.py

REM Запускаем приложение
echo 🌐 Запуск FastAPI сервера...
echo 📍 Откройте браузер: http://localhost:8000
echo 📚 API документация: http://localhost:8000/docs
echo.

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

pause

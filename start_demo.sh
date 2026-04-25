#!/bin/bash
# Скрипт для быстрого запуска ДЕМО без Docker и PostgreSQL (использует SQLite)

echo "🚀 Investment Intelligence Hub - Fast Demo Mode"
echo "=============================================="

# 1. Создаем виртуальное окружение, если нет
if [ ! -d "venv" ]; then
    echo "📦 Создание виртуального окружения..."
    python3 -m venv venv
fi

# 2. Активируем его
source venv/bin/activate

# 3. Устанавливаем зависимости
echo "📥 Установка зависимостей..."
pip install -r requirements.txt

# 4. Настраиваем окружение на SQLite для Демо
# Это позволит запустить проект без установленного PostgreSQL
export DATABASE_URL_LOCAL="sqlite:///./demo.db"

# 5. Инициализируем БД данными
echo "💾 Создание и наполнение демо-базы (SQLite)..."
python init_db.py

# 6. Запускаем Бэкенд в фоне
echo "🌐 Запуск Бэкенда на http://localhost:8000..."
uvicorn app.main:app --port 8000 &
BACKEND_PID=$!

# 7. Запускаем Фронтенд
echo "🎨 Запуск Фронтенда на http://localhost:3000..."
cd frontend
python3 server.py 3000 &
FRONTEND_PID=$!

echo ""
echo "✅ ВСЕ ЗАПУЩЕНО!"
echo "📍 Фронтенд: http://localhost:3000"
echo "📚 Бэкенд API: http://localhost:8000/docs"
echo ""
echo "Для остановки нажмите Ctrl+C"

# Ожидание прерывания
trap "kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait

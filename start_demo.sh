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
pip install -r requirements.txt -q

# 4. Настраиваем окружение на SQLite для Демо
export DATABASE_URL_LOCAL="sqlite:///./demo.db"
export ADMIN_PASSWORD="Admin@12345!"
export SECRET_KEY="demo-secret-key-for-local-testing-change-in-prod"
export ENABLE_METRICS="false"
export ALLOWED_ORIGINS="*"

# 5. Инициализируем БД данными
# (init_db.py автоматически обнаруживает устаревшую схему и пересоздаёт таблицы)
echo "💾 Создание и наполнение демо-базы (SQLite)..."
python init_db.py

# 6. Запускаем Бэкенд в фоне
echo "🌐 Запуск Бэкенда на http://localhost:8000..."
uvicorn app.main:app --port 8000 &
BACKEND_PID=$!

# 7. Ждём пока бэкенд запустится
sleep 3

# 8. Запускаем Фронтенд
echo "🎨 Запуск Фронтенда на http://localhost:3000..."
cd frontend
python3 server.py 3000 &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ ВСЕ ЗАПУЩЕНО!"
echo "📍 Фронтенд:    http://localhost:3000"
echo "📚 API Docs:    http://localhost:8000/docs"
echo "🏥 Health:      http://localhost:8000/health"
echo ""
echo "🔑 Admin login: admin / Admin@12345!"
echo ""
echo "Для остановки нажмите Ctrl+C"

# Ожидание прерывания
trap "echo 'Останавливаем...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait

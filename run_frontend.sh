#!/bin/bash

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Starting Investment Intelligence Hub UX ===${NC}"

# Переходим в директорию фронтенда
cd frontend

# Находим свободный порт (по умолчанию 3000)
PORT=3000

echo -e "${GREEN}Starting local HTTP server on http://localhost:${PORT}${NC}"
echo -e "Press Ctrl+C to stop."

# Запускаем python http.server
python -m http.server $PORT

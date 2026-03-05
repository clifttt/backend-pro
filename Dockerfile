# 1. Скачиваем легкую версию Python
FROM python:3.10-slim

# 2. Отключаем создание лишних файлов мусора
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 3. Создаем рабочую папку внутри контейнера
WORKDIR /app

# 4. Сначала копируем список покупок (чтобы кэшировалось)
COPY requirements.txt .

# 5. Устанавливаем библиотеки
RUN pip install --no-cache-dir -r requirements.txt

# 6. Теперь копируем весь остальной код
COPY . .

# 7. Команда запуска (как нажать кнопку Power)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# 🚀 Investment Intelligence Hub

[![CI Pipeline](https://github.com/clifttt/backend-pro/actions/workflows/ci.yml/badge.svg)](https://github.com/clifttt/backend-pro/actions)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker)](https://www.docker.com/)

**Investment Intelligence Hub** — это мощная Backend-платформа для автоматизированного сбора, агрегации и анализа венчурных инвестиций и данных о стартапах. Проект разработан в рамках курса *Advanced Backend & DevOps*.

---

## 👥 Команда и Роли

*   **Zhangir** — *Backend Developer*: Архитектура БД, разработка REST API, логика фильтрации и поиска.
*   **Nurislam** — *Data Engineer*: Сбор данных (Scraping), нормализация, очистка и оценка качества данных.
*   **Nurym** — *DevOps Engineer*: Контейнеризация, настройка CI/CD Pipelines, управление инфраструктурой.

---

## 🛠 Технологический Стек

*   **Core:** Python 3.10+, FastAPI, Uvicorn
*   **Database:** PostgreSQL (SQLAlchemy 2.0 + Alembic)
*   **Data Processing:** BeautifulSoup4, Requests (Robust Sessions), APScheduler
*   **Infrastructure:** Docker, Docker Compose, GitHub Actions (CI/CD)
*   **Quality:** Flake8 (Linting), Pytest-style Integration Tests

---

## ✨ Ключевые Возможности

### 📡 Продвинутый Collector
*   **Anti-Blocking:** Ротация User-Agent, поддержка прокси, адаптивные задержки и экспоненциальный backoff при ошибках.
*   **Robust Fetching:** Обработка таймаутов и автоматические повторы запросов.
*   **Automation:** Встроенный планировщик задач для регулярного обновления данных.

### 🧹 Интеллектуальный Processor
*   **Normalization:** Очистка данных от мусора, приведение к единому формату названий и дат.
*   **Entity Extraction:** Извлечение сумм, дат и тегов из неструктурированного текста с помощью regex.
*   **Quality Score:** Автоматическая оценка качества данных в базе (0-100%).

### ⚡ Мощный REST API
*   **Unified Search:** Полнотекстовый поиск по всем сущностям (стартапы, инвесторы, инвестиции).
*   **Advanced Filtering:** Сложная фильтрация, сортировка и пагинация во всех эндпоинтах.
*   **Live Stats:** Агрегированная статистика по инвестициям и топ-стартапам.

---

## 🚀 Быстрый Старт

### Через Docker (Рекомендуется)

1.  **Создайте .env файл:**
    ```bash
    cp .env.example .env
    ```
2.  **Запустите контейнеры:**
    ```bash
    docker-compose up -d --build
    ```
3.  **Инициализируйте БД:**
    ```bash
    docker-compose exec web python init_db.py
    ```

### Локальный запуск

1.  **Установите зависимости:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Настройте БД** и укажите URL в `.env`.
3.  **Запустите сервер:**
    ```bash
    uvicorn app.main:app --reload
    ```

---

## 📖 Документация API

После запуска документация доступна по адресам:
*   **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
*   **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Основные Эндпоинты
*   `GET /search?q=query` — Глобальный поиск.
*   `GET /startups` — Список стартапов с фильтрацией по странам и дате основания.
*   `GET /investors` — Данные об инвесторах и их фокусах.
*   `GET /investments` — История инвестиций с фильтрацией по суммам и раундам.
*   `GET /statistics` — Аналитические данные по рынку.

---

## 📁 Структура Проекта

```text
├── app/                  # Основное FastAPI приложение
│   ├── main.py           # Эндпоинты и бизнес-логика API
│   ├── models/           # SQLAlchemy ORM сущности
│   └── db.py             # Настройки подключения к БД
├── alembic/              # Миграции базы данных
├── .github/              # GitHub Actions (CI/CD Pipeline)
├── enhanced_collector.py # Модуль сбора данных с защитой от блокировок
├── normalizer.py         # Модуль очистки и оценки качества данных
├── scheduler_main.py     # Планировщик фоновых задач
├── init_db.py            # Скрипт инициализации и посева (Seed) данных
├── test_api.py           # Скрипт автоматизированного тестирования API
└── docker-compose.yml    # Оркестрация контейнеров
```

---

## 🛡 CI/CD

В проекте настроен **GitHub Actions**. На каждый пуш или PR:
1.  Проверяется стиль кода (`flake8`).
2.  Собирается Docker-образ.
3.  Проверяется корректность запуска приложения в контейнере.

---

## 📝 Лицензия

Проект распространяется под лицензией MIT.
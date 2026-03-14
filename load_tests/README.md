# Load Testing — Investment Intelligence Hub
## Week 13: Нагрузочное тестирование с Locust

### Установка
```bash
# Активируй venv, затем:
pip install locust==2.29.0
```

### Запуск с веб-интерфейсом
```bash
# 1. Убедись, что API запущен на http://localhost:8000
uvicorn app.main:app --reload

# 2. Запусти Locust
locust -f load_tests/locustfile.py --host http://localhost:8000

# 3. Открой http://localhost:8089 в браузере
#    Укажи: Users=100, Spawn rate=10, и нажми Start
```

### Headless (CI / отчёты)
```bash
locust -f load_tests/locustfile.py \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 60s \
  --host http://localhost:8000 \
  --html load_tests/report.html \
  --csv load_tests/results
```

### Профили нагрузки

| Сценарий        | Users | Spawn Rate | Duration | Цель          |
|-----------------|-------|-----------|----------|---------------|
| Smoke test      | 10    | 2         | 30s      | Базовая работа |
| Load test       | 100   | 10        | 60s      | Целевая нагрузка |
| Stress test     | 200   | 20        | 120s     | Предел системы |
| Spike test      | 500   | 100       | 30s      | Пиковая нагрузка |

### Пример результатов (100 users, 60s, local machine)

| Endpoint                  | RPS  | P50 (ms) | P95 (ms) | Errors |
|---------------------------|------|----------|----------|--------|
| GET /startups             | 48.2 | 12       | 45       | 0%     |
| GET /investors            | 32.1 | 11       | 38       | 0%     |
| GET /search               | 28.5 | 18       | 72       | 0%     |
| GET /statistics           | 15.3 | 8        | 21       | 0%     |
| GET /startups/{id}        | 22.4 | 9        | 28       | 0%*    |
| GET /health               | 10.2 | 6        | 15       | 0%     |
| **Total**                 | **156.7** | **11** | **52** | **0%** |

*404s считаются успехом (случайные ID)

### Архитектура тестов

```
InvestmentHubUser (weight=default)
├── list_startups          (weight=4) — страничный просмотр
├── list_startups_filtered (weight=3) — фильтр по стране  
├── list_investors         (weight=3) — список инвесторов
├── list_investments       (weight=3) — список с фильтром раунда
├── search_all             (weight=3) — поиск по всем ресурсам
├── search_startups        (weight=2) — поиск стартапов
├── get_statistics         (weight=2) — статистика (кэш)
├── get_startup_detail     (weight=2) — детали стартапа
├── get_investor_detail    (weight=2) — детали инвестора
├── investments_amount     (weight=1) — фильтр по сумме
└── health_check           (weight=1) — проверка здоровья

HeavyReadUser (weight=1, fast — имитирует аналитику)
├── bulk_startups  (weight=5) — 100 записей за раз
├── stats_polling  (weight=3) — частые запросы статистики
└── search_wildcard(weight=2) — широкий поиск
```

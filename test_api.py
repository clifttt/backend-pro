#!/usr/bin/env python3
"""
Test API endpoints
Проверка что все REST API эндпоинты работают корректно
"""

import requests
import json
import time
from typing import Optional

# Конфигурация
BASE_URL = "http://localhost:8000"
TIMEOUT = 5

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_test(test_name: str, status: bool, details: str = ""):
    """Вывести результат теста"""
    icon = f"{Colors.GREEN}✅{Colors.RESET}" if status else f"{Colors.RED}❌{Colors.RESET}"
    status_text = f"{Colors.GREEN}PASSED{Colors.RESET}" if status else f"{Colors.RED}FAILED{Colors.RESET}"
    print(f"{icon} {test_name}: {status_text}")
    if details:
        print(f"   └─ {details}")


def test_endpoint(method: str, endpoint: str, expected_status: int = 200, params: Optional[dict] = None) -> tuple[bool, str]:
    """Протестировать эндпоинт"""
    try:
        url = f"{BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, params=params, timeout=TIMEOUT)
        else:
            return False, "Unsupported method"
        
        success = response.status_code == expected_status
        
        if success:
            data = response.json()
            return True, json.dumps(data, indent=2, ensure_ascii=False)[:200] + "..."
        else:
            return False, f"Status code: {response.status_code} (expected {expected_status})"
    
    except requests.exceptions.ConnectionError:
        return False, "Connection error - сервер не запущен на http://localhost:8000"
    except Exception as e:
        return False, str(e)


def main():
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}🧪 Investment Intelligence Hub - API Tests{Colors.RESET}")
    print(f"{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    # Проверяем подключение к серверу
    print("📍 Проверка подключения к серверу...")
    time.sleep(1)
    
    success, details = test_endpoint("GET", "/health")
    if not success:
        print(f"{Colors.RED}❌ Не удается подключиться к серверу!{Colors.RESET}")
        print(f"   Убедитесь что сервер запущен: uvicorn app.main:app --reload")
        print(f"   Детали: {details}")
        return 1
    
    print(f"{Colors.GREEN}✅ Сервер доступен на {BASE_URL}{Colors.RESET}\n")
    
    # Категория: Info endpoints
    print(f"{Colors.YELLOW}📚 Info Endpoints:{Colors.RESET}")
    
    test_endpoint("GET", "/")
    print_test("GET /", *test_endpoint("GET", "/"))
    
    success, details = test_endpoint("GET", "/health")
    print_test("GET /health", success, "✅ Database connected" if success else details)
    
    # Категория: Startups
    print(f"\n{Colors.YELLOW}🏢 Startups Endpoints:{Colors.RESET}")
    
    success, details = test_endpoint("GET", "/startups")
    print_test("GET /startups", success, "Список стартапов с пагинацией" if success else details)
    
    success, details = test_endpoint("GET", "/startups", params={"page": 1, "per_page": 5})
    print_test("GET /startups (с пагинацией)", success, "page=1, per_page=5" if success else details)
    
    success, details = test_endpoint("GET", "/startups", params={"country": "USA"})
    print_test("GET /startups?country=USA", success, "Фильтрация по стране" if success else details)
    
    success, details = test_endpoint("GET", "/startups", params={"name": "Tech"})
    print_test("GET /startups?name=Tech", success, "Поиск по названию" if success else details)
    
    success, details = test_endpoint("GET", "/startups/1")
    print_test("GET /startups/1", success, "Конкретный стартап" if success else details)
    
    # Категория: Investors
    print(f"\n{Colors.YELLOW}👥 Investors Endpoints:{Colors.RESET}")
    
    success, details = test_endpoint("GET", "/investors")
    print_test("GET /investors", success, "Список инвесторов" if success else details)
    
    success, details = test_endpoint("GET", "/investors", params={"page": 1, "per_page": 5})
    print_test("GET /investors (пагинация)", success, "page=1, per_page=5" if success else details)
    
    success, details = test_endpoint("GET", "/investors", params={"name": "Sequoia"})
    print_test("GET /investors?name=Sequoia", success, "Поиск по названию" if success else details)
    
    success, details = test_endpoint("GET", "/investors/1")
    print_test("GET /investors/1", success, "Конкретный инвестор" if success else details)
    
    # Категория: Investments
    print(f"\n{Colors.YELLOW}💰 Investments Endpoints:{Colors.RESET}")
    
    success, details = test_endpoint("GET", "/investments")
    print_test("GET /investments", success, "Список инвестиций" if success else details)
    
    success, details = test_endpoint("GET", "/investments", params={"startup_id": 1})
    print_test("GET /investments?startup_id=1", success, "Инвестиции стартапа" if success else details)
    
    success, details = test_endpoint("GET", "/investments", params={"investor_id": 1})
    print_test("GET /investments?investor_id=1", success, "Инвестиции инвестора" if success else details)
    
    success, details = test_endpoint("GET", "/investments", params={"round": "Seed"})
    print_test("GET /investments?round=Seed", success, "Инвестиции раунда Seed" if success else details)
    
    success, details = test_endpoint("GET", "/investments", params={"min_amount": 100000, "max_amount": 1000000})
    print_test("GET /investments (диапазон сумм)", success, "min_amount, max_amount" if success else details)
    
    success, details = test_endpoint("GET", "/investments/1")
    print_test("GET /investments/1", success, "Конкретная инвестиция" if success else details)
    
    # Категория: Statistics
    print(f"\n{Colors.YELLOW}📊 Statistics Endpoints:{Colors.RESET}")
    
    success, details = test_endpoint("GET", "/statistics")
    print_test("GET /statistics", success, "Общая статистика" if success else details)
    
    # Итоги
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.GREEN}🎉 Все тесты завершены!{Colors.RESET}")
    print(f"\n📚 Интерактивная документация доступна по ссылкам:")
    print(f"   🔗 Swagger UI: {BASE_URL}/docs")
    print(f"   🔗 ReDoc: {BASE_URL}/redoc")
    print(f"   🔗 OpenAPI JSON: {BASE_URL}/openapi.json")
    print(f"\n{Colors.BLUE}{'='*60}{Colors.RESET}\n")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

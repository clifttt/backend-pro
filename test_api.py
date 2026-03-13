#!/usr/bin/env python3
"""
Test API endpoints
Проверка что все REST API эндпоинты работают корректно
Week 8 Update: Добавлены тесты валидации структуры ответов и примеры документации
"""

import requests
import json
import time
from typing import Optional
from datetime import datetime

# Конфигурация
BASE_URL = "http://localhost:8000"
TIMEOUT = 5

# Счётчики тестов
TESTS_PASSED = 0
TESTS_FAILED = 0

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_test(test_name: str, status: bool, details: str = ""):
    """Вывести результат теста"""
    global TESTS_PASSED, TESTS_FAILED
    
    if status:
        TESTS_PASSED += 1
    else:
        TESTS_FAILED += 1
    
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
            if endpoint in ["/docs", "/redoc"]:
                return True, "HTML Page"
            data = response.json()
            return True, json.dumps(data, indent=2, ensure_ascii=False)[:200] + "..."
        else:
            return False, f"Status code: {response.status_code} (expected {expected_status})"
    
    except requests.exceptions.ConnectionError:
        return False, "Connection error - сервер не запущен на http://localhost:8000"
    except Exception as e:
        return False, str(e)


def validate_pagination_response(response_data: dict) -> tuple[bool, str]:
    """Проверить структуру ответа с пагинацией"""
    try:
        if "data" not in response_data or "meta" not in response_data:
            return False, "Missing 'data' or 'meta' field"
        
        meta = response_data["meta"]
        required_fields = ["total", "page", "per_page", "pages"]
        
        for field in required_fields:
            if field not in meta:
                return False, f"Missing field in meta: {field}"
            if not isinstance(meta[field], int):
                return False, f"Field {field} should be integer"
        
        if meta["page"] < 1:
            return False, "Page should be >= 1"
        if meta["per_page"] < 1:
            return False, "Per page should be >= 1"
        if meta["pages"] < 0:
            return False, "Pages should be >= 0"
        if meta["total"] < 0:
            return False, "Total should be >= 0"
            
        return True, "Pagination structure is valid"
    except Exception as e:
        return False, str(e)


def validate_startup_response(startup: dict) -> tuple[bool, str]:
    """Проверить структуру стартапа"""
    try:
        required_fields = ["id", "name"]
        optional_fields = ["country", "investments"]
        
        for field in required_fields:
            if field not in startup:
                return False, f"Missing required field: {field}"
        
        if not isinstance(startup["id"], int):
            return False, "ID should be integer"
        if not isinstance(startup["name"], str):
            return False, "Name should be string"
        
        return True, "Startup structure is valid"
    except Exception as e:
        return False, str(e)


def validate_investor_response(investor: dict) -> tuple[bool, str]:
    """Проверить структуру инвестора"""
    try:
        required_fields = ["id", "name"]
        
        for field in required_fields:
            if field not in investor:
                return False, f"Missing required field: {field}"
        
        if not isinstance(investor["id"], int):
            return False, "ID should be integer"
        if not isinstance(investor["name"], str):
            return False, "Name should be string"
        
        return True, "Investor structure is valid"
    except Exception as e:
        return False, str(e)


def validate_investment_response(investment: dict) -> tuple[bool, str]:
    """Проверить структуру инвестиции"""
    try:
        required_fields = ["id", "startup_id", "investor_id"]
        
        for field in required_fields:
            if field not in investment:
                return False, f"Missing required field: {field}"
        
        if not isinstance(investment["id"], int):
            return False, "ID should be integer"
        if not isinstance(investment["startup_id"], int):
            return False, "startup_id should be integer"
        if not isinstance(investment["investor_id"], int):
            return False, "investor_id should be integer"
        
        return True, "Investment structure is valid"
    except Exception as e:
        return False, str(e)


def main():
    global TESTS_PASSED, TESTS_FAILED
    
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}🧪 Investment Intelligence Hub - API Tests (Week 8){Colors.RESET}")
    print(f"{Colors.BLUE}{'='*70}{Colors.RESET}\n")
    
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
    
    success, details = test_endpoint("GET", "/")
    print_test("GET /", success, "Root endpoint" if success else details)
    
    success, details = test_endpoint("GET", "/health")
    print_test("GET /health", success, "✅ Database connected" if success else details)
    
    # Категория: Startups
    print(f"\n{Colors.YELLOW}🏢 Startups Endpoints:{Colors.RESET}")
    
    success, details = test_endpoint("GET", "/startups")
    print_test("GET /startups", success, "Список стартапов с пагинацией" if success else details)
    
    # Проверяем структуру ответа на /startups
    if success:
        try:
            response = requests.get(f"{BASE_URL}/startups", timeout=TIMEOUT)
            data = response.json()
            valid, msg = validate_pagination_response(data)
            print_test("  └─ Valida pagination structure", valid, msg)
            
            # Проверяем структуру стартапов в ответе
            if valid and len(data.get("data", [])) > 0:
                startup = data["data"][0]
                valid_startup, msg = validate_startup_response(startup)
                print_test("  └─ Valid startup structure", valid_startup, msg)
        except Exception as e:
            print_test("  └─ Response validation", False, str(e))
    
    success, details = test_endpoint("GET", "/startups", params={"page": 1, "per_page": 5})
    print_test("GET /startups (с пагинацией page=1, per_page=5)", success, details if not success else "✅" )
    
    success, details = test_endpoint("GET", "/startups", params={"country": "USA"})
    print_test("GET /startups?country=USA", success, "Фильтрация по стране" if success else details)
    
    success, details = test_endpoint("GET", "/startups", params={"name": "Tech"})
    print_test("GET /startups?name=Tech", success, "Поиск по названию" if success else details)

    # Новые параметры сортировки
    success, details = test_endpoint("GET", "/startups", params={"sort_by": "name", "sort_order": "asc"})
    print_test("GET /startups?sort_by=name&sort_order=asc", success, "Сортировка по имени (asc)" if success else details)
    
    success, details = test_endpoint("GET", "/startups", params={"sort_by": "name", "sort_order": "desc"})
    print_test("GET /startups?sort_by=name&sort_order=desc", success, "Сортировка по имени (desc)" if success else details)

    success, details = test_endpoint("GET", "/startups/1")
    print_test("GET /startups/1", success, "Конкретный стартап" if success else details)
    
    # Проверяем структуру отдельного стартапа
    if success:
        try:
            response = requests.get(f"{BASE_URL}/startups/1", timeout=TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                valid, msg = validate_startup_response(data)
                print_test("  └─ Valid startup detail structure", valid, msg)
        except:
            pass
    
    # Категория: Investors
    print(f"\n{Colors.YELLOW}👥 Investors Endpoints:{Colors.RESET}")
    
    success, details = test_endpoint("GET", "/investors")
    print_test("GET /investors", success, "Список инвесторов" if success else details)
    
    # Проверяем структуру ответа на /investors
    if success:
        try:
            response = requests.get(f"{BASE_URL}/investors", timeout=TIMEOUT)
            data = response.json()
            valid, msg = validate_pagination_response(data)
            print_test("  └─ Valid pagination structure", valid, msg)
            
            # Проверяем структуру инвесторов в ответе
            if valid and len(data.get("data", [])) > 0:
                investor = data["data"][0]
                valid_investor, msg = validate_investor_response(investor)
                print_test("  └─ Valid investor structure", valid_investor, msg)
        except Exception as e:
            print_test("  └─ Response validation", False, str(e))
    
    success, details = test_endpoint("GET", "/investors", params={"page": 1, "per_page": 5})
    print_test("GET /investors (пагинация page=1, per_page=5)", success, details if not success else "✅")
    
    success, details = test_endpoint("GET", "/investors", params={"name": "Sequoia"})
    print_test("GET /investors?name=Sequoia", success, "Поиск по названию" if success else details)

    # Проверка сортировки инвесторов
    success, details = test_endpoint("GET", "/investors", params={"sort_order": "desc"})
    print_test("GET /investors?sort_order=desc", success, "Сортировка по имени (desc)" if success else details)

    success, details = test_endpoint("GET", "/investors", params={"sort_order": "asc"})
    print_test("GET /investors?sort_order=asc", success, "Сортировка по имени (asc)" if success else details)

    success, details = test_endpoint("GET", "/investors/1")
    print_test("GET /investors/1", success, "Конкретный инвестор" if success else details)
    
    # Проверяем структуру отдельного инвестора
    if success:
        try:
            response = requests.get(f"{BASE_URL}/investors/1", timeout=TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                valid, msg = validate_investor_response(data)
                print_test("  └─ Valid investor detail structure", valid, msg)
        except:
            pass
    
    # Категория: Investments
    print(f"\n{Colors.YELLOW}💰 Investments Endpoints:{Colors.RESET}")
    
    success, details = test_endpoint("GET", "/investments")
    print_test("GET /investments", success, "Список инвестиций" if success else details)
    
    # Проверяем структуру ответа на /investments
    if success:
        try:
            response = requests.get(f"{BASE_URL}/investments", timeout=TIMEOUT)
            data = response.json()
            valid, msg = validate_pagination_response(data)
            print_test("  └─ Valid pagination structure", valid, msg)
            
            # Проверяем структуру инвестиций в ответе
            if valid and len(data.get("data", [])) > 0:
                investment = data["data"][0]
                valid_investment, msg = validate_investment_response(investment)
                print_test("  └─ Valid investment structure", valid_investment, msg)
        except Exception as e:
            print_test("  └─ Response validation", False, str(e))
    
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

    # Новые тесты: полнотекстовый поиск
    print(f"\n{Colors.YELLOW}🔎 Search Endpoints:{Colors.RESET}")
    
    success, details = test_endpoint("GET", "/search", params={"q": "Tech"})
    print_test("GET /search?q=Tech", success, "Поиск по всем ресурсам" if success else details)

    success, details = test_endpoint("GET", "/search", params={"q": "USA", "search_type": "startup"})
    print_test("GET /search?q=USA&search_type=startup", success, "Поиск только стартапов" if success else details)

    success, details = test_endpoint("GET", "/search", params={"q": "Seed", "search_type": "investment", "limit": 5})
    print_test("GET /search?q=Seed&search_type=investment&limit=5", success, "Поиск инвестиций" if success else details)
    
    # Week 8: Тесты для новых функций документации и примеров
    print(f"\n{Colors.YELLOW}📖 Week 8 - Documentation & Examples:{Colors.RESET}")
    
    # Проверяем доступность OpenAPI схемы
    success, details = test_endpoint("GET", "/openapi.json")
    print_test("GET /openapi.json", success, "OpenAPI schema доступна" if success else details)
    
    if success:
        try:
            response = requests.get(f"{BASE_URL}/openapi.json", timeout=TIMEOUT)
            if response.status_code == 200:
                schema = response.json()
                if "components" in schema and "schemas" in schema["components"]:
                    components = schema["components"]["schemas"]
                    
                    # Проверяем наличие примеров в моделях
                    example_models = ["StartupRead", "InvestorRead", "InvestmentRead", "PaginationMeta"]
                    models_with_examples = 0
                    
                    for model_name in example_models:
                        if model_name in components:
                            model_schema = components[model_name]
                            if "example" in model_schema:
                                models_with_examples += 1
                    
                    print_test(f"  └─ Models with examples ({models_with_examples}/{len(example_models)})", 
                               models_with_examples > 0, f"{models_with_examples} models have examples")
        except:
            pass
    
    success, details = test_endpoint("GET", "/docs")
    print_test("GET /docs", success, "Swagger UI доступна" if success else details)
    
    success, details = test_endpoint("GET", "/redoc")
    print_test("GET /redoc", success, "ReDoc доступна" if success else details)

    # Итоги
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}")
    print(f"{Colors.BLUE}🎯 Test Summary:{Colors.RESET}")
    print(f"{Colors.GREEN}Passed: {TESTS_PASSED}{Colors.RESET} | {Colors.RED}Failed: {TESTS_FAILED}{Colors.RESET}")
    print(f"Total: {TESTS_PASSED + TESTS_FAILED} tests")
    
    if TESTS_FAILED == 0:
        print(f"{Colors.GREEN}🎉 Все тесты пройдены успешно!{Colors.RESET}")
    else:
        print(f"{Colors.YELLOW}⚠️  {TESTS_FAILED} тестов не прошли{Colors.RESET}")
    
    print(f"\n📚 Интерактивная документация доступна по ссылкам:")
    print(f"   🔗 Swagger UI: {BASE_URL}/docs")
    print(f"   🔗 ReDoc: {BASE_URL}/redoc")
    print(f"   🔗 OpenAPI JSON: {BASE_URL}/openapi.json")
    print(f"\n{Colors.BLUE}{'='*70}{Colors.RESET}\n")
    
    return 0 if TESTS_FAILED == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

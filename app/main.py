from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, func
from typing import List, Optional
from pydantic import BaseModel, Field
import datetime
import time
from enum import Enum

from app.db import get_db, engine
from app.models import Base, Startup, Investor, Investment
from fastapi.middleware.cors import CORSMiddleware
from app.auth import create_access_token, get_current_user, ACCESS_TOKEN_EXPIRE_MINUTES
from prometheus_fastapi_instrumentator import Instrumentator

# ==================== Simple In-Memory Stats Cache ====================
_stats_cache: dict = {"data": None, "expires_at": 0.0}
_STATS_TTL_SECONDS = 60  # Cache statistics for 60 seconds

# Создаем таблицы при старте
Base.metadata.create_all(bind=engine)

# Создаем приложение с расширенной документацией
app = FastAPI(
    title="Investment Intelligence Hub API",
    description="""
🚀 **Полнофункциональный REST API для анализа инвестиционных данных**

### Возможности:
- ✅ Полнотекстовый поиск (Full-text search)
- ✅ Сложная фильтрация по множеству параметров
- ✅ Сортировка по различным полям
- ✅ Пагинация для больших результатов
- ✅ Статистика и аналитика
- ✅ Интерактивная документация (Swagger UI)

### Основные ресурсы:
- **Startups** - Информация о стартапах
- **Investors** - Данные об инвесторах
- **Investments** - История инвестиций
- **Search** - Полнотекстовый поиск по всем ресурсам

### Версии:
- v1.0.0: REST API базовый уровень
- v2.0.0: REST API продвинутый уровень (Неделя 8)
    """,
    version="2.0.0",
    openapi_tags=[
        {"name": "Info", "description": "Основная информация о сервере"},
        {"name": "Startups", "description": "Управление стартапами"},
        {"name": "Investors", "description": "Управление инвесторами"},
        {"name": "Investments", "description": "Управление инвестициями"},
        {"name": "Search", "description": "Полнотекстовый поиск"},
        {"name": "Statistics", "description": "Аналитика и статистика"},
    ]
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем запросы с любых доменов для локальной разработки
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Prometheus Metrics ====================
# Exposes /metrics endpoint for Prometheus scraping (Week 14)
Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
).instrument(app).expose(app, include_in_schema=True, tags=["Monitoring"])


# ==================== Pydantic Models (для JSON ответов) ====================

class InvestmentRead(BaseModel):
    """Модель для чтения данных об инвестиции"""
    id: int = Field(..., description="Уникальный идентификатор инвестиции")
    startup_id: int = Field(..., description="ID стартапа")
    investor_id: int = Field(..., description="ID инвестора")
    round: Optional[str] = Field(None, description="Раунд финансирования (например, 'Series A', 'Seed')")
    amount_usd: Optional[float] = Field(None, description="Сумма инвестиции в USD")
    date: Optional[datetime.date] = Field(None, description="Дата объявления инвестиции")
    status: Optional[str] = Field(None, description="Статус инвестиции")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 1,
                "startup_id": 5,
                "investor_id": 3,
                "round": "Series B",
                "amount_usd": 15000000.00,
                "date": "2024-06-15",
                "status": "Active"
            }
        }
    }


class InvestorRead(BaseModel):
    """Модель для чтения данных об инвесторе"""
    id: int = Field(..., description="Уникальный идентификатор инвестора")
    name: str = Field(..., description="Имя или название инвестора")
    fund_name: Optional[str] = Field(None, description="Название фонда")
    focus_area: Optional[str] = Field(None, description="Область инвестирования")
    investments: List[InvestmentRead] = Field(default_factory=list, description="Список инвестиций инвестора")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 3,
                "name": "Sequoia Capital",
                "fund_name": "Sequoia Capital Fund XIX",
                "focus_area": "Technology, SaaS",
                "investments": [
                    {
                        "id": 1,
                        "startup_id": 5,
                        "investor_id": 3,
                        "round": "Series B",
                        "amount_usd": 15000000.00,
                        "date": "2024-06-15",
                        "status": "Active"
                    }
                ]
            }
        }
    }


class StartupCreate(BaseModel):
    name: str = Field(..., description="Название стартапа")
    country: Optional[str] = Field(None, description="Страна базирования стартапа")
    description: Optional[str] = Field(None, description="Описание стартапа")
    founded_year: Optional[int] = Field(None, description="Год основания")
    status: Optional[str] = Field("Active", description="Статус стартапа")

# Model configurations down below...
class StartupRead(BaseModel):
    """Модель для чтения данных о стартапе"""
    id: int = Field(..., description="Уникальный идентификатор стартапа")
    name: str = Field(..., description="Название стартапа")
    country: Optional[str] = Field(None, description="Страна базирования стартапа")
    description: Optional[str] = Field(None, description="Описание стартапа")
    founded_year: Optional[int] = Field(None, description="Год основания")
    status: Optional[str] = Field(None, description="Статус стартапа (Active, Acquired, etc.)")
    investments: List[InvestmentRead] = Field(default_factory=list, description="Список инвестиций в стартап")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": 5,
                "name": "OpenAI",
                "country": "USA",
                "description": "AI research and deployment company",
                "founded_year": 2015,
                "status": "Active",
                "investments": [
                    {
                        "id": 1,
                        "startup_id": 5,
                        "investor_id": 3,
                        "round": "Series B",
                        "amount_usd": 15000000.00,
                        "date": "2024-06-15",
                        "status": "Active"
                    }
                ]
            }
        }
    }


class PaginationMeta(BaseModel):
    """Метаданные о пагинации"""
    total: int = Field(..., description="Общее количество элементов")
    page: int = Field(..., description="Текущая страница")
    per_page: int = Field(..., description="Элементов на странице")
    pages: int = Field(..., description="Общее количество страниц")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 100,
                "page": 1,
                "per_page": 10,
                "pages": 10
            }
        }
    }


# Enums для сортировки
class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


# Response модели
class StartupListResponse(BaseModel):
    """Ответ со списком стартапов"""
    data: List[StartupRead] = Field(..., description="Список стартапов")
    meta: PaginationMeta = Field(..., description="Метаданные пагинации")

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [
                    {
                        "id": 5,
                        "name": "OpenAI",
                        "country": "USA",
                        "investments": []
                    },
                    {
                        "id": 6,
                        "name": "Tesla",
                        "country": "USA",
                        "investments": []
                    }
                ],
                "meta": {
                    "total": 100,
                    "page": 1,
                    "per_page": 10,
                    "pages": 10
                }
            }
        }
    }


class InvestorListResponse(BaseModel):
    """Ответ со списком инвесторов"""
    data: List[InvestorRead] = Field(..., description="Список инвесторов")
    meta: PaginationMeta = Field(..., description="Метаданные пагинации")

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [
                    {
                        "id": 1,
                        "name": "Andrey Volkov",
                        "investments": []
                    },
                    {
                        "id": 3,
                        "name": "Sequoia Capital",
                        "investments": []
                    }
                ],
                "meta": {
                    "total": 50,
                    "page": 1,
                    "per_page": 10,
                    "pages": 5
                }
            }
        }
    }


class InvestmentListResponse(BaseModel):
    """Ответ со списком инвестиций"""
    data: List[InvestmentRead] = Field(..., description="Список инвестиций")
    meta: PaginationMeta = Field(..., description="Метаданные пагинации")

    model_config = {
        "json_schema_extra": {
            "example": {
                "data": [
                    {
                        "id": 1,
                        "startup_id": 5,
                        "investor_id": 3,
                        "round": "Series B",
                        "amount_usd": 15000000.00,
                        "announced_date": "2024-06-15"
                    }
                ],
                "meta": {
                    "total": 200,
                    "page": 1,
                    "per_page": 10,
                    "pages": 20
                }
            }
        }
    }


# Модель для комбинированного поиска
class SearchResult(BaseModel):
    """Результат поиска"""
    id: int = Field(..., description="Идентификатор объекта")
    type: str = Field(..., description="Тип объекта: 'startup', 'investor' или 'investment'")
    name: str = Field(..., description="Имя или название объекта")
    details: dict = Field(..., description="Дополнительные детали")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 5,
                "type": "startup",
                "name": "OpenAI",
                "details": {"country": "USA"}
            }
        }
    }


class UnifiedSearchResponse(BaseModel):
    """Ответ с результатами поиска"""
    results: List[SearchResult] = Field(..., description="Список результатов поиска")
    total: int = Field(..., description="Общее количество найденных результатов")
    query: str = Field(..., description="Поисковый запрос")

    model_config = {
        "json_schema_extra": {
            "example": {
                "results": [
                    {
                        "id": 5,
                        "type": "startup",
                        "name": "OpenAI",
                        "details": {"country": "USA"}
                    }
                ],
                "total": 1,
                "query": "OpenAI"
            }
        }
    }


# ==================== Root Endpoints ====================

@app.get("/", tags=["Info"])
def read_root():
    """Главная страница API"""
    return {
        "message": "Investment Intelligence Hub API",
        "version": "1.0.0",
        "status": "✅ Сервер работает!",
        "endpoints": {
            "startups": "/startups",
            "investors": "/investors",
            "investments": "/investments",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }


@app.post("/token", tags=["Auth"])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Простая заглушка - принимаем admin:secret
    if form_data.username != "admin" or form_data.password != "secret":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/health", tags=["Info"])
def health_check(db: Session = Depends(get_db)):
    """Проверка здоровья сервера и БД"""
    try:
        # Попытка выполнить простой запрос
        startup_count = db.query(Startup).count()
        investor_count = db.query(Investor).count()
        investment_count = db.query(Investment).count()

        return {
            "status": "✅ OK",
            "database": "✅ Connected",
            "statistics": {
                "startups": startup_count,
                "investors": investor_count,
                "investments": investment_count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


# ==================== Startups Endpoints ====================

@app.post("/startups", response_model=StartupRead, status_code=status.HTTP_201_CREATED, tags=["Startups"])
def create_startup(startup: StartupCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_user)):
    """
    Создать новый стартап. 
    **Внимание**: Это защищенный метод, требуется JWT токен!
    """
    db_startup = Startup(
        name=startup.name,
        country=startup.country,
        description=startup.description,
        founded_year=startup.founded_year,
        status=startup.status
    )
    db.add(db_startup)
    db.commit()
    db.refresh(db_startup)
    return StartupRead.from_orm(db_startup)

@app.get("/startups", response_model=StartupListResponse, tags=["Startups"])
def get_startups(
    page: int = Query(1, ge=1, description="Номер страницы (начиная с 1)"),
    per_page: int = Query(10, ge=1, le=100, description="Количество элементов на странице"),
    country: Optional[str] = Query(None, description="Фильтр по стране"),
    name: Optional[str] = Query(None, description="Поиск по названию (содержит)"),
    sort_by: str = Query("name", description="Поле для сортировки (name, founded_year)"),
    sort_order: SortOrder = Query(SortOrder.asc, description="Порядок сортировки (asc или desc)"),
    db: Session = Depends(get_db)
):
    """
    Получить список стартапов с пагинацией, фильтрацией и сортировкой
    
    ### Параметры:
    - **page**: Номер страницы (по умолчанию 1)
    - **per_page**: Количество элементов на странице (1-100, по умолчанию 10)
    - **country**: Фильтрация по стране (опционально)
    - **name**: Поиск по названию/части названия (опционально)
    - **sort_by**: Поле для сортировки: 'name' или 'founded_year' (по умолчанию 'name')
    - **sort_order**: 'asc' для возрастания или 'desc' для убывания (по умолчанию 'asc')
    """
    # Use joinedload to prevent N+1 queries when loading startup.investments
    query = db.query(Startup).options(joinedload(Startup.investments))

    # Применяем фильтры
    if country:
        query = query.filter(Startup.country == country)
    if name:
        query = query.filter(Startup.name.ilike(f"%{name}%"))

    # Применяем сортировку
    if sort_by == "founded_year":
        order_column = Startup.founded_year
    else:  # default to name
        order_column = Startup.name

    if sort_order == SortOrder.desc:
        query = query.order_by(order_column.desc())
    else:
        query = query.order_by(order_column.asc())

    # Получаем общее количество (subquery to avoid count issues with joinedload)
    count_query = db.query(func.count(Startup.id))
    if country:
        count_query = count_query.filter(Startup.country == country)
    if name:
        count_query = count_query.filter(Startup.name.ilike(f"%{name}%"))
    total = count_query.scalar()

    # Применяем пагинацию
    skip = (page - 1) * per_page
    startups = query.offset(skip).limit(per_page).all()

    # Вычисляем количество страниц
    pages = (total + per_page - 1) // per_page

    return StartupListResponse(
        data=[StartupRead.from_orm(s) for s in startups],
        meta=PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
    )


@app.get("/startups/{startup_id}", response_model=StartupRead, tags=["Startups"])
def get_startup(startup_id: int, db: Session = Depends(get_db)):
    """Получить информацию о конкретном стартапе по ID"""
    startup = (
        db.query(Startup)
        .options(joinedload(Startup.investments))
        .filter(Startup.id == startup_id)
        .first()
    )

    if not startup:
        raise HTTPException(status_code=404, detail=f"Startup with ID {startup_id} not found")

    return StartupRead.from_orm(startup)


# ==================== Investors Endpoints ====================

@app.get("/investors", response_model=InvestorListResponse, tags=["Investors"])
def get_investors(
    page: int = Query(1, ge=1, description="Номер страницы (начиная с 1)"),
    per_page: int = Query(10, ge=1, le=100, description="Количество элементов на странице"),
    name: Optional[str] = Query(None, description="Поиск по названию (содержит)"),
    sort_by: str = Query("name", description="Поле для сортировки (name)"),
    sort_order: SortOrder = Query(SortOrder.asc, description="Порядок сортировки (asc или desc)"),
    db: Session = Depends(get_db)
):
    """
    Получить список инвесторов с пагинацией, фильтрацией и сортировкой
    
    ### Параметры:
    - **page**: Номер страницы (по умолчанию 1)
    - **per_page**: Количество элементов на странице (1-100, по умолчанию 10)
    - **name**: Поиск по названию/части названия (опционально)
    - **sort_by**: Поле для сортировки (по умолчанию 'name')
    - **sort_order**: 'asc' для возрастания или 'desc' для убывания (по умолчанию 'asc')
    """
    # Use joinedload to prevent N+1 queries
    query = db.query(Investor).options(joinedload(Investor.investments))

    # Применяем фильтры
    if name:
        query = query.filter(Investor.name.ilike(f"%{name}%"))

    # Применяем сортировку (по умолчанию по имени)
    if sort_order == SortOrder.desc:
        query = query.order_by(Investor.name.desc())
    else:
        query = query.order_by(Investor.name.asc())

    # Получаем общее количество
    count_query = db.query(func.count(Investor.id))
    if name:
        count_query = count_query.filter(Investor.name.ilike(f"%{name}%"))
    total = count_query.scalar()

    # Применяем пагинацию
    skip = (page - 1) * per_page
    investors = query.offset(skip).limit(per_page).all()

    # Вычисляем количество страниц
    pages = (total + per_page - 1) // per_page

    return InvestorListResponse(
        data=[InvestorRead.from_orm(i) for i in investors],
        meta=PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
    )


@app.get("/investors/{investor_id}", response_model=InvestorRead, tags=["Investors"])
def get_investor(investor_id: int, db: Session = Depends(get_db)):
    """Получить информацию об инвесторе по ID"""
    investor = (
        db.query(Investor)
        .options(joinedload(Investor.investments))
        .filter(Investor.id == investor_id)
        .first()
    )

    if not investor:
        raise HTTPException(status_code=404, detail=f"Investor with ID {investor_id} not found")

    return InvestorRead.from_orm(investor)


# ==================== Investments Endpoints ====================

@app.get("/investments", response_model=InvestmentListResponse, tags=["Investments"])
def get_investments(
    page: int = Query(1, ge=1, description="Номер страницы (начиная с 1)"),
    per_page: int = Query(10, ge=1, le=100, description="Количество элементов на странице"),
    startup_id: Optional[int] = Query(None, description="Фильтр по стартапу"),
    investor_id: Optional[int] = Query(None, description="Фильтр по инвестору"),
    round: Optional[str] = Query(None, description="Фильтр по раунду (Seed, Series A и т.д.)"),
    min_amount: Optional[float] = Query(None, ge=0, description="Минимальная сумма в USD"),
    max_amount: Optional[float] = Query(None, ge=0, description="Максимальная сумма в USD"),
    status: Optional[str] = Query(None, description="Фильтр по статусу (Active, Concluded и т.д.)"),
    sort_by: str = Query("date", description="Поле для сортировки (date, amount_usd)"),
    sort_order: SortOrder = Query(SortOrder.desc, description="Порядок сортировки (asc или desc)"),
    db: Session = Depends(get_db)
):
    """
    Получить список инвестиций с расширенной фильтрацией и сортировкой
    
    ### Параметры:
    - **page**: Номер страницы (по умолчанию 1)
    - **per_page**: Количество элементов на странице (1-100, по умолчанию 10)
    - **startup_id**: Фильтр по ID стартапа (опционально)
    - **investor_id**: Фильтр по ID инвестора (опционально)
    - **round**: Фильтр по типу раунда (опционально)
    - **min_amount**: Минимальная сумма инвестиции (опционально)
    - **max_amount**: Максимальная сумма инвестиции (опционально)
    - **status**: Фильтр по статусу (опционально)
    - **sort_by**: Поле для сортировки: 'date' или 'amount_usd' (по умолчанию 'date')
    - **sort_order**: 'asc' для возрастания или 'desc' для убывания (по умолчанию 'desc')
    """
    query = db.query(Investment)

    # Применяем фильтры
    if startup_id:
        query = query.filter(Investment.startup_id == startup_id)
    if investor_id:
        query = query.filter(Investment.investor_id == investor_id)
    if round:
        query = query.filter(Investment.round == round)
    if status:
        query = query.filter(Investment.status == status)
    if min_amount is not None:
        query = query.filter(Investment.amount_usd >= min_amount)
    if max_amount is not None:
        query = query.filter(Investment.amount_usd <= max_amount)

    # Применяем сортировку
    if sort_by == "amount_usd":
        order_column = Investment.amount_usd
    else:  # default to date
        order_column = Investment.date

    if sort_order == SortOrder.desc:
        query = query.order_by(order_column.desc())
    else:
        query = query.order_by(order_column.asc())

    # Получаем общее количество
    total = query.count()

    # Применяем пагинацию
    skip = (page - 1) * per_page
    investments = query.offset(skip).limit(per_page).all()

    # Вычисляем количество страниц
    pages = (total + per_page - 1) // per_page

    return InvestmentListResponse(
        data=[InvestmentRead.from_orm(i) for i in investments],
        meta=PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )
    )


@app.get("/investments/{investment_id}", response_model=InvestmentRead, tags=["Investments"])
def get_investment(investment_id: int, db: Session = Depends(get_db)):
    """Получить информацию об инвестиции по ID"""
    investment = db.query(Investment).filter(Investment.id == investment_id).first()

    if not investment:
        raise HTTPException(status_code=404, detail=f"Investment with ID {investment_id} not found")

    return InvestmentRead.from_orm(investment)


# ==================== Advanced Search Endpoint ====================

@app.get("/search", response_model=UnifiedSearchResponse, tags=["Search"])
def unified_search(
    q: str = Query(..., min_length=1, description="Поисковое выражение"),
    search_type: Optional[str] = Query(
        None, description="Тип поиска: 'startup', 'investor', 'investment' или пусто для всех"
    ),
    limit: int = Query(20, ge=1, le=100, description="Максимум результатов"),
    db: Session = Depends(get_db)
):
    """
    🔍 Полнотекстовый поиск по всем ресурсам

    Выполняет поиск по названиям и описаниям стартапов, инвесторов и инвестиций.
    
    ### Параметры:
    - **q**: Поисковое выражение (обязательно)
    - **search_type**: Ограничить поиск типом ресурса (опционально)
    - **limit**: Максимум результатов (по умолчанию 20, максимум 100)
    
    ### Примеры использования:
    - `/search?q=tech` - поиск по всем ресурсам
    - `/search?q=OpenAI&search_type=startup` - поиск только стартапов
    - `/search?q=Sequoia&search_type=investor` - поиск только инвесторов
    """
    results = []
    search_query = f"%{q}%"

    # Поиск в стартапах
    if search_type is None or search_type == "startup":
        startups = db.query(Startup).filter(
            or_(
                Startup.name.ilike(search_query),
                Startup.country.ilike(search_query)
            )
        ).limit(limit).all()

        for startup in startups:
            results.append(SearchResult(
                id=startup.id,
                type="startup",
                name=startup.name,
                details={
                    "country": startup.country,
                    "founded_year": startup.founded_year,
                    "description": startup.description or "N/A"
                }
            ))

    # Поиск в инвесторах
    if search_type is None or search_type == "investor":
        investors = db.query(Investor).filter(
            Investor.name.ilike(search_query)
        ).limit(limit).all()

        for investor in investors:
            results.append(SearchResult(
                id=investor.id,
                type="investor",
                name=investor.name,
                details={
                    "fund_name": investor.fund_name or "N/A",
                    "focus_area": investor.focus_area or "N/A"
                }
            ))

    # Поиск в инвестициях (по раунду)
    if search_type is None or search_type == "investment":
        investments = db.query(Investment).filter(
            or_(
                Investment.round.ilike(search_query),
                Investment.status.ilike(search_query)
            )
        ).limit(limit).all()

        for investment in investments:
            startup = db.query(Startup).filter(Startup.id == investment.startup_id).first()
            investor = db.query(Investor).filter(Investor.id == investment.investor_id).first()

            results.append(SearchResult(
                id=investment.id,
                type="investment",
                name=f"{startup.name if startup else 'Unknown'} - {investor.name if investor else 'Unknown'}",
                details={
                    "round": investment.round,
                    "amount_usd": float(investment.amount_usd),
                    "status": investment.status,
                    "date": investment.date.isoformat() if investment.date else None
                }
            ))

    return UnifiedSearchResponse(
        results=results[:limit],
        total=len(results),
        query=q
    )


# ==================== Statistics Endpoints ====================

@app.get("/statistics", tags=["Statistics"])
def get_statistics(db: Session = Depends(get_db)):
    """Получить общую статистику по БД (кэшируется на 60 секунд)"""
    global _stats_cache
    now = time.time()

    # Return cached result if still fresh
    if _stats_cache["data"] is not None and now < _stats_cache["expires_at"]:
        return _stats_cache["data"]

    # Общие подсчеты
    startup_count = db.query(func.count(Startup.id)).scalar()
    investor_count = db.query(func.count(Investor.id)).scalar()
    investment_count = db.query(func.count(Investment.id)).scalar()

    # Статистика по инвестициям
    total_investment = db.query(func.sum(Investment.amount_usd)).scalar() or 0
    avg_investment = db.query(func.avg(Investment.amount_usd)).scalar() or 0

    # Топ стартапы по сумме инвестиций
    top_startups = db.query(
        Startup.name,
        func.sum(Investment.amount_usd).label("total_investment")
    ).join(Investment).group_by(Startup.id).order_by(
        func.sum(Investment.amount_usd).desc()
    ).limit(5).all()

    result = {
        "summary": {
            "total_startups": startup_count,
            "total_investors": investor_count,
            "total_investments": investment_count
        },
        "investment_stats": {
            "total_amount_usd": float(total_investment),
            "average_amount_usd": float(avg_investment) if avg_investment else None
        },
        "top_startups": [
            {"name": name, "total_investment_usd": float(amount)}
            for name, amount in top_startups
        ],
        "cache": {
            "cached": False,
            "expires_in_seconds": _STATS_TTL_SECONDS
        }
    }

    # Store in cache
    _stats_cache["data"] = result
    _stats_cache["expires_at"] = now + _STATS_TTL_SECONDS

    # Mark as fresh (not from cache) for the first caller
    return result


# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )
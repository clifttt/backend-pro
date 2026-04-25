"""
main.py — Investment Intelligence Hub API
FastAPI application with full CRUD, JWT auth, FTS, caching, and monitoring.
"""
from fastapi import FastAPI, Depends, HTTPException, Query, status, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from sqlalchemy import or_, func, text
from typing import List, Optional
from pydantic import BaseModel, Field, EmailStr
import datetime
import time
import logging
import json
from enum import Enum

from app.db import get_db, engine
from app.models import Base, Startup, Investor, Investment, User
from fastapi.middleware.cors import CORSMiddleware
from app.auth import (
    create_access_token,
    get_current_user,
    authenticate_user,
    create_user,
    get_user_by_username,
    get_user_by_email,
    ensure_default_admin,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    UserCreate,
    UserPublic,
)
from prometheus_fastapi_instrumentator import Instrumentator
import os

# ==================== Simple In-Memory Stats Cache ====================
_stats_cache: dict = {"data": None, "expires_at": 0.0}
_STATS_TTL_SECONDS = 60  # Cache statistics for 60 seconds

# Создаем таблицы при старте
Base.metadata.create_all(bind=engine)

# ==================== First-boot seed admin user ====================
def _seed_admin():
    """Ensure at least one admin user exists on startup."""
    from sqlalchemy.orm import sessionmaker
    _Session = sessionmaker(bind=engine)
    db = _Session()
    try:
        ensure_default_admin(db)
    finally:
        db.close()

_seed_admin()

# ==================== Logging Configuration ====================
logger = logging.getLogger("invest_hub")
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)

# ==================== Application Setup ====================
app = FastAPI(
    title="Investment Intelligence Hub API",
    description="""
🚀 **Полнофункциональный REST API для анализа инвестиционных данных**

### Возможности:
- ✅ Полнотекстовый поиск (Full-text search via PostgreSQL tsvector)
- ✅ Сложная фильтрация по множеству параметров
- ✅ Сортировка по различным полям
- ✅ Пагинация для больших результатов
- ✅ Статистика и аналитика
- ✅ JWT-авторизация с реальной БД пользователей
- ✅ Регистрация и вход пользователей
- ✅ Интерактивная документация (Swagger UI)
- ✅ Prometheus метрики

### Основные ресурсы:
- **Startups** — Информация о стартапах
- **Investors** — Данные об инвесторах
- **Investments** — История инвестиций
- **Search** — Полнотекстовый поиск по всем ресурсам
- **Auth** — Регистрация, вход, профиль

### Auth flow:
1. `POST /auth/register` — создать аккаунт
2. `POST /token` — получить JWT токен
3. Передавать `Authorization: Bearer <token>` для защищённых методов
    """,
    version="3.0.0",
    openapi_tags=[
        {"name": "Info", "description": "Основная информация о сервере"},
        {"name": "Auth", "description": "Регистрация и авторизация"},
        {"name": "Startups", "description": "Управление стартапами"},
        {"name": "Investors", "description": "Управление инвесторами"},
        {"name": "Investments", "description": "Управление инвестициями"},
        {"name": "Search", "description": "Полнотекстовый поиск"},
        {"name": "Statistics", "description": "Аналитика и статистика"},
    ],
)

# Настройка CORS
_allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# ==================== Security Headers Middleware ====================
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' cdn.jsdelivr.net fonts.googleapis.com; "
        "img-src 'self' data: fastapi.tiangolo.com;"
    )
    return response

# ==================== Prometheus Metrics ====================
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

# ==================== Logging Middleware ====================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    if request.url.path not in ["/metrics", "/health"]:
        log_data = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": "INFO",
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client": request.client.host if request.client else "unknown",
        }
        logger.info(json.dumps(log_data))

    return response


# ==================== Pydantic Models ====================

class InvestorMinimal(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class StartupMinimal(BaseModel):
    id: int
    name: str
    country: Optional[str] = None
    model_config = {"from_attributes": True}


class InvestmentRead(BaseModel):
    id: int = Field(..., description="Уникальный идентификатор инвестиции")
    startup_id: int = Field(..., description="ID стартапа")
    investor_id: int = Field(..., description="ID инвестора")
    round: Optional[str] = Field(None, description="Раунд финансирования")
    amount_usd: Optional[float] = Field(None, description="Сумма в USD")
    date: Optional[datetime.date] = Field(None, description="Дата")
    status: Optional[str] = Field(None, description="Статус")
    startup: Optional[StartupMinimal] = None
    investor: Optional[InvestorMinimal] = None

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
                "status": "Active",
            }
        },
    }


class InvestorRead(BaseModel):
    id: int = Field(..., description="Уникальный идентификатор инвестора")
    name: str = Field(..., description="Имя или название инвестора")
    fund_name: Optional[str] = Field(None, description="Название фонда")
    focus_area: Optional[str] = Field(None, description="Область инвестирования")
    investments: List[InvestmentRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class StartupCreate(BaseModel):
    name: str = Field(..., description="Название стартапа")
    country: Optional[str] = Field(None, description="Страна")
    description: Optional[str] = Field(None, description="Описание")
    founded_year: Optional[int] = Field(None, description="Год основания")
    status: Optional[str] = Field("Active", description="Статус")
    source_url: Optional[str] = Field(None, description="URL источника данных")


class StartupRead(BaseModel):
    id: int = Field(..., description="ID стартапа")
    name: str = Field(..., description="Название")
    country: Optional[str] = Field(None)
    description: Optional[str] = Field(None)
    founded_year: Optional[int] = Field(None)
    status: Optional[str] = Field(None)
    source_url: Optional[str] = Field(None, description="Источник данных (Crunchbase/PitchBook)")
    investments: List[InvestmentRead] = Field(default_factory=list)

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
                "source_url": "https://www.crunchbase.com/organization/openai",
                "investments": [],
            }
        },
    }


class PaginationMeta(BaseModel):
    total: int = Field(..., description="Всего элементов")
    page: int = Field(..., description="Текущая страница")
    per_page: int = Field(..., description="Элементов на странице")
    pages: int = Field(..., description="Всего страниц")

    model_config = {
        "json_schema_extra": {"example": {"total": 100, "page": 1, "per_page": 10, "pages": 10}}
    }


class SortOrder(str, Enum):
    asc = "asc"
    desc = "desc"


class StartupListResponse(BaseModel):
    data: List[StartupRead]
    meta: PaginationMeta


class InvestorListResponse(BaseModel):
    data: List[InvestorRead]
    meta: PaginationMeta


class InvestmentListResponse(BaseModel):
    data: List[InvestmentRead]
    meta: PaginationMeta


class SearchResult(BaseModel):
    id: int
    type: str
    name: str
    details: dict

    model_config = {
        "json_schema_extra": {
            "example": {"id": 5, "type": "startup", "name": "OpenAI", "details": {"country": "USA"}}
        }
    }


class UnifiedSearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query: str


# ==================== Root Endpoints ====================

@app.get("/", tags=["Info"])
def read_root():
    """Главная страница API"""
    return {
        "message": "Investment Intelligence Hub API",
        "version": "3.0.0",
        "status": "✅ Сервер работает!",
        "docs": "/docs",
        "endpoints": {
            "startups": "/startups",
            "investors": "/investors",
            "investments": "/investments",
            "search": "/search",
            "statistics": "/statistics",
            "auth": {"register": "/auth/register", "login": "/token", "profile": "/auth/me"},
        },
    }


@app.get("/health", tags=["Info"])
def health_check(db: Session = Depends(get_db)):
    """Проверка здоровья сервера и БД"""
    try:
        startup_count = db.query(Startup).count()
        investor_count = db.query(Investor).count()
        investment_count = db.query(Investment).count()
        user_count = db.query(User).count()

        return {
            "status": "✅ OK",
            "database": "✅ Connected",
            "statistics": {
                "startups": startup_count,
                "investors": investor_count,
                "investments": investment_count,
                "users": user_count,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


# ==================== Auth Endpoints ====================

@app.post("/token", tags=["Auth"], summary="Получить JWT токен")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Войти и получить JWT access token.

    **Учётные данные по умолчанию:** `admin` / `Admin@12345!`
    (переопределяются через env-переменную `ADMIN_PASSWORD`)
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверное имя пользователя или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@app.post("/auth/register", response_model=UserPublic, status_code=201, tags=["Auth"])
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Зарегистрировать нового пользователя.

    - **username**: уникальное имя пользователя
    - **email**: уникальный e-mail
    - **password**: минимум 8 символов
    """
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Пароль должен содержать минимум 8 символов",
        )
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Пользователь '{user_data.username}' уже существует",
        )
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{user_data.email}' уже используется",
        )
    user = create_user(db, user_data)
    return UserPublic.model_validate(user)


@app.get("/auth/me", response_model=UserPublic, tags=["Auth"])
def get_current_user_profile(
    current_username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить профиль текущего пользователя (требует JWT)."""
    user = get_user_by_username(db, current_username)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return UserPublic.model_validate(user)


# ==================== Startups Endpoints ====================

@app.post(
    "/startups",
    response_model=StartupRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Startups"],
)
def create_startup(
    startup: StartupCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """
    Создать новый стартап. **Требуется JWT токен.**
    """
    db_startup = Startup(
        name=startup.name,
        country=startup.country,
        description=startup.description,
        founded_year=startup.founded_year,
        status=startup.status,
        source_url=startup.source_url,
    )
    db.add(db_startup)
    db.commit()
    db.refresh(db_startup)
    return StartupRead.model_validate(db_startup)


@app.get("/startups", response_model=StartupListResponse, tags=["Startups"])
def get_startups(
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(10, ge=1, le=100, description="Элементов на странице (макс. 100)"),
    country: Optional[str] = Query(None, description="Фильтр по стране"),
    name: Optional[str] = Query(None, description="Поиск по названию"),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    founded_year_from: Optional[int] = Query(None, description="Год основания (от)"),
    founded_year_to: Optional[int] = Query(None, description="Год основания (до)"),
    sort_by: str = Query("name", description="Поле сортировки: name, founded_year"),
    sort_order: SortOrder = Query(SortOrder.asc, description="asc или desc"),
    db: Session = Depends(get_db),
):
    """
    Список стартапов с пагинацией, фильтрацией и сортировкой.
    """
    query = db.query(Startup).options(joinedload(Startup.investments))

    if country:
        query = query.filter(Startup.country.ilike(f"%{country}%"))
    if name:
        query = query.filter(Startup.name.ilike(f"%{name}%"))
    if status:
        query = query.filter(Startup.status.ilike(f"%{status}%"))
    if founded_year_from:
        query = query.filter(Startup.founded_year >= founded_year_from)
    if founded_year_to:
        query = query.filter(Startup.founded_year <= founded_year_to)

    order_column = Startup.founded_year if sort_by == "founded_year" else Startup.name
    query = query.order_by(
        order_column.desc() if sort_order == SortOrder.desc else order_column.asc()
    )

    # Separate count query
    count_q = db.query(func.count(Startup.id))
    if country:
        count_q = count_q.filter(Startup.country.ilike(f"%{country}%"))
    if name:
        count_q = count_q.filter(Startup.name.ilike(f"%{name}%"))
    if status:
        count_q = count_q.filter(Startup.status.ilike(f"%{status}%"))
    if founded_year_from:
        count_q = count_q.filter(Startup.founded_year >= founded_year_from)
    if founded_year_to:
        count_q = count_q.filter(Startup.founded_year <= founded_year_to)
    total = count_q.scalar()

    skip = (page - 1) * per_page
    startups = query.offset(skip).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    return StartupListResponse(
        data=[StartupRead.model_validate(s) for s in startups],
        meta=PaginationMeta(total=total, page=page, per_page=per_page, pages=pages),
    )


@app.get("/startups/{startup_id}", response_model=StartupRead, tags=["Startups"])
def get_startup(startup_id: int, db: Session = Depends(get_db)):
    """Получить стартап по ID"""
    startup = (
        db.query(Startup)
        .options(joinedload(Startup.investments))
        .filter(Startup.id == startup_id)
        .first()
    )
    if not startup:
        raise HTTPException(status_code=404, detail=f"Startup {startup_id} not found")
    return StartupRead.model_validate(startup)


@app.put("/startups/{startup_id}", response_model=StartupRead, tags=["Startups"])
def update_startup(
    startup_id: int,
    startup: StartupCreate,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Обновить стартап по ID. **Требуется JWT токен.**"""
    db_startup = db.query(Startup).filter(Startup.id == startup_id).first()
    if not db_startup:
        raise HTTPException(status_code=404, detail=f"Startup {startup_id} not found")
    for field, value in startup.model_dump(exclude_unset=True).items():
        setattr(db_startup, field, value)
    db.commit()
    db.refresh(db_startup)
    return StartupRead.model_validate(db_startup)


@app.delete("/startups/{startup_id}", status_code=204, tags=["Startups"])
def delete_startup(
    startup_id: int,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
):
    """Удалить стартап по ID. **Требуется JWT токен.**"""
    db_startup = db.query(Startup).filter(Startup.id == startup_id).first()
    if not db_startup:
        raise HTTPException(status_code=404, detail=f"Startup {startup_id} not found")
    db.delete(db_startup)
    db.commit()


# ==================== Investors Endpoints ====================

@app.get("/investors", response_model=InvestorListResponse, tags=["Investors"])
def get_investors(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    name: Optional[str] = Query(None, description="Поиск по имени"),
    focus_area: Optional[str] = Query(None, description="Фильтр по области инвестирования"),
    sort_by: str = Query("name"),
    sort_order: SortOrder = Query(SortOrder.asc),
    db: Session = Depends(get_db),
):
    """Список инвесторов с пагинацией и фильтрацией."""
    query = db.query(Investor).options(joinedload(Investor.investments))

    if name:
        query = query.filter(Investor.name.ilike(f"%{name}%"))
    if focus_area:
        query = query.filter(Investor.focus_area.ilike(f"%{focus_area}%"))

    query = query.order_by(
        Investor.name.desc() if sort_order == SortOrder.desc else Investor.name.asc()
    )

    count_q = db.query(func.count(Investor.id))
    if name:
        count_q = count_q.filter(Investor.name.ilike(f"%{name}%"))
    if focus_area:
        count_q = count_q.filter(Investor.focus_area.ilike(f"%{focus_area}%"))
    total = count_q.scalar()

    skip = (page - 1) * per_page
    investors = query.offset(skip).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    return InvestorListResponse(
        data=[InvestorRead.model_validate(i) for i in investors],
        meta=PaginationMeta(total=total, page=page, per_page=per_page, pages=pages),
    )


@app.get("/investors/export/csv", tags=["Investors"])
def export_investors_csv(db: Session = Depends(get_db)):
    """Экспорт всех инвесторов в CSV."""
    import csv
    import io
    from fastapi.responses import StreamingResponse

    investors = (
        db.query(Investor)
        .options(joinedload(Investor.investments))
        .order_by(Investor.name.asc())
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(["ID", "Name", "Fund Name", "Focus Area", "Portfolio Size"])
    for inv in investors:
        writer.writerow(
            [
                inv.id,
                inv.name or "",
                inv.fund_name or "",
                inv.focus_area or "",
                len(inv.investments) if inv.investments else 0,
            ]
        )

    output.seek(0)
    content = "\ufeff" + output.getvalue()

    return StreamingResponse(
        iter([content.encode("utf-8")]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=investors_export.csv"},
    )


@app.get("/investors/{investor_id}", response_model=InvestorRead, tags=["Investors"])
def get_investor(investor_id: int, db: Session = Depends(get_db)):
    """Получить инвестора по ID"""
    investor = (
        db.query(Investor)
        .options(joinedload(Investor.investments))
        .filter(Investor.id == investor_id)
        .first()
    )
    if not investor:
        raise HTTPException(status_code=404, detail=f"Investor {investor_id} not found")
    return InvestorRead.model_validate(investor)


# ==================== Investments Endpoints ====================

@app.get("/investments", response_model=InvestmentListResponse, tags=["Investments"])
def get_investments(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    startup_id: Optional[int] = Query(None),
    investor_id: Optional[int] = Query(None),
    round: Optional[str] = Query(None, description="Seed, Series A, Series B..."),
    min_amount: Optional[float] = Query(None, ge=0),
    max_amount: Optional[float] = Query(None, ge=0),
    status: Optional[str] = Query(None),
    sort_by: str = Query("date", description="date или amount_usd"),
    sort_order: SortOrder = Query(SortOrder.desc),
    db: Session = Depends(get_db),
):
    """
    Список инвестиций с расширенной фильтрацией.
    """
    query = db.query(Investment).options(
        joinedload(Investment.startup), joinedload(Investment.investor)
    )

    if startup_id:
        query = query.filter(Investment.startup_id == startup_id)
    if investor_id:
        query = query.filter(Investment.investor_id == investor_id)
    if round:
        query = query.filter(Investment.round.ilike(f"%{round}%"))
    if status:
        query = query.filter(Investment.status.ilike(f"%{status}%"))
    if min_amount is not None:
        query = query.filter(Investment.amount_usd >= min_amount)
    if max_amount is not None:
        query = query.filter(Investment.amount_usd <= max_amount)

    order_column = Investment.amount_usd if sort_by == "amount_usd" else Investment.date
    query = query.order_by(
        order_column.desc() if sort_order == SortOrder.desc else order_column.asc()
    )

    total = query.count()
    skip = (page - 1) * per_page
    investments = query.offset(skip).limit(per_page).all()
    pages = (total + per_page - 1) // per_page

    return InvestmentListResponse(
        data=[InvestmentRead.model_validate(i) for i in investments],
        meta=PaginationMeta(total=total, page=page, per_page=per_page, pages=pages),
    )


@app.get("/investments/{investment_id}", response_model=InvestmentRead, tags=["Investments"])
def get_investment(investment_id: int, db: Session = Depends(get_db)):
    """Получить инвестицию по ID"""
    investment = db.query(Investment).filter(Investment.id == investment_id).first()
    if not investment:
        raise HTTPException(status_code=404, detail=f"Investment {investment_id} not found")
    return InvestmentRead.model_validate(investment)


# ==================== Full-Text Search ====================

def _fts_supported(db: Session) -> bool:
    """Returns True if connected to PostgreSQL (supports tsvector FTS)."""
    try:
        db.execute(text("SELECT to_tsvector('english', 'test')"))
        return True
    except Exception:
        return False


@app.get("/search", response_model=UnifiedSearchResponse, tags=["Search"])
def unified_search(
    q: str = Query(..., min_length=1, description="Поисковое выражение"),
    search_type: Optional[str] = Query(
        None, description="startup | investor | investment (пусто = все)"
    ),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    🔍 Полнотекстовый поиск по всем ресурсам.

    На PostgreSQL используется **tsvector** для точного FTS.
    На SQLite используется LIKE (для тестов).
    """
    results: List[SearchResult] = []
    use_fts = _fts_supported(db)
    search_query = f"%{q}%"

    # ── Startups ──────────────────────────────────────────────────────
    if search_type is None or search_type == "startup":
        if use_fts:
            startups = db.execute(
                text(
                    """
                    SELECT id, name, country, description, founded_year, status, source_url
                    FROM startups
                    WHERE to_tsvector('english', coalesce(name,'') || ' ' || coalesce(description,'') || ' ' || coalesce(country,''))
                          @@ plainto_tsquery('english', :q)
                    LIMIT :lim
                    """
                ),
                {"q": q, "lim": limit},
            ).fetchall()
            for row in startups:
                results.append(
                    SearchResult(
                        id=row.id,
                        type="startup",
                        name=row.name,
                        details={
                            "country": row.country,
                            "founded_year": row.founded_year,
                            "description": row.description or "N/A",
                            "source_url": row.source_url,
                        },
                    )
                )
        else:
            for s in (
                db.query(Startup)
                .filter(
                    or_(
                        Startup.name.ilike(search_query),
                        Startup.country.ilike(search_query),
                        Startup.description.ilike(search_query),
                    )
                )
                .limit(limit)
                .all()
            ):
                results.append(
                    SearchResult(
                        id=s.id,
                        type="startup",
                        name=s.name,
                        details={
                            "country": s.country,
                            "founded_year": s.founded_year,
                            "description": s.description or "N/A",
                        },
                    )
                )

    # ── Investors ─────────────────────────────────────────────────────
    if search_type is None or search_type == "investor":
        if use_fts:
            investors = db.execute(
                text(
                    """
                    SELECT id, name, fund_name, focus_area
                    FROM investors
                    WHERE to_tsvector('english', coalesce(name,'') || ' ' || coalesce(focus_area,''))
                          @@ plainto_tsquery('english', :q)
                    LIMIT :lim
                    """
                ),
                {"q": q, "lim": limit},
            ).fetchall()
            for row in investors:
                results.append(
                    SearchResult(
                        id=row.id,
                        type="investor",
                        name=row.name,
                        details={"fund_name": row.fund_name or "N/A", "focus_area": row.focus_area or "N/A"},
                    )
                )
        else:
            for inv in (
                db.query(Investor)
                .filter(
                    or_(
                        Investor.name.ilike(search_query),
                        Investor.focus_area.ilike(search_query),
                    )
                )
                .limit(limit)
                .all()
            ):
                results.append(
                    SearchResult(
                        id=inv.id,
                        type="investor",
                        name=inv.name,
                        details={"fund_name": inv.fund_name or "N/A", "focus_area": inv.focus_area or "N/A"},
                    )
                )

    # ── Investments ───────────────────────────────────────────────────
    if search_type is None or search_type == "investment":
        matches = (
            db.query(Investment)
            .filter(
                or_(
                    Investment.round.ilike(search_query),
                    Investment.status.ilike(search_query),
                )
            )
            .limit(limit)
            .all()
        )
        for inv in matches:
            startup = db.query(Startup).filter(Startup.id == inv.startup_id).first()
            investor = db.query(Investor).filter(Investor.id == inv.investor_id).first()
            results.append(
                SearchResult(
                    id=inv.id,
                    type="investment",
                    name=f"{startup.name if startup else 'Unknown'} — {investor.name if investor else 'Unknown'}",
                    details={
                        "round": inv.round,
                        "amount_usd": float(inv.amount_usd) if inv.amount_usd else None,
                        "status": inv.status,
                        "date": inv.date.isoformat() if inv.date else None,
                    },
                )
            )

    return UnifiedSearchResponse(results=results[:limit], total=len(results[:limit]), query=q)


# ==================== Statistics Endpoint ====================

@app.get("/statistics", tags=["Statistics"])
def get_statistics(db: Session = Depends(get_db)):
    """Общая статистика по БД (кэшируется на 60 секунд в памяти)."""
    global _stats_cache
    now = time.time()

    if _stats_cache["data"] is not None and now < _stats_cache["expires_at"]:
        cached = dict(_stats_cache["data"])
        cached["cache"] = {"cached": True, "expires_in_seconds": int(_stats_cache["expires_at"] - now)}
        return cached

    startup_count = db.query(func.count(Startup.id)).scalar()
    investor_count = db.query(func.count(Investor.id)).scalar()
    investment_count = db.query(func.count(Investment.id)).scalar()

    total_investment = db.query(func.sum(Investment.amount_usd)).scalar() or 0
    avg_investment = db.query(func.avg(Investment.amount_usd)).scalar() or 0

    top_startups = (
        db.query(Startup.name, func.sum(Investment.amount_usd).label("total"))
        .join(Investment)
        .group_by(Startup.id)
        .order_by(func.sum(Investment.amount_usd).desc())
        .limit(5)
        .all()
    )

    # Round distribution
    rounds = (
        db.query(Investment.round, func.count(Investment.id).label("cnt"))
        .group_by(Investment.round)
        .order_by(func.count(Investment.id).desc())
        .all()
    )

    # Country distribution
    countries = (
        db.query(Startup.country, func.count(Startup.id).label("cnt"))
        .filter(Startup.country.isnot(None))
        .group_by(Startup.country)
        .order_by(func.count(Startup.id).desc())
        .limit(10)
        .all()
    )

    result = {
        "summary": {
            "total_startups": startup_count,
            "total_investors": investor_count,
            "total_investments": investment_count,
        },
        "investment_stats": {
            "total_amount_usd": float(total_investment),
            "average_amount_usd": float(avg_investment) if avg_investment else None,
        },
        "top_startups": [
            {"name": name, "total_investment_usd": float(amount)} for name, amount in top_startups
        ],
        "rounds_distribution": [
            {"round": r, "count": c} for r, c in rounds
        ],
        "countries_distribution": [
            {"country": c, "startups": cnt} for c, cnt in countries
        ],
        "cache": {"cached": False, "expires_in_seconds": _STATS_TTL_SECONDS},
    }

    _stats_cache["data"] = result
    _stats_cache["expires_at"] = now + _STATS_TTL_SECONDS
    return result


# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )
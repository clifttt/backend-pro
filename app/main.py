from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import date

from app.db import get_db, engine
from app.models import Base, Startup, Investor, Investment

# Создаем таблицы при старте
Base.metadata.create_all(bind=engine)

# Создаем приложение
app = FastAPI(
    title="Investment Intelligence Hub",
    description="API для агрегации и анализа данных о стартапах и венчурных инвестициях",
    version="1.0.0"
)


# ==================== Pydantic Models (для JSON ответов) ====================

class InvestmentRead(BaseModel):
    id: int
    startup_id: int
    investor_id: int
    round: Optional[str] = None
    amount_usd: Optional[float] = None
    announced_date: Optional[date] = None

    class Config:
        from_attributes = True


class InvestorRead(BaseModel):
    id: int
    name: str
    investments: List[InvestmentRead] = []

    class Config:
        from_attributes = True


class StartupRead(BaseModel):
    id: int
    name: str
    country: Optional[str] = None
    investments: List[InvestmentRead] = []

    class Config:
        from_attributes = True


class PaginationMeta(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int


class StartupListResponse(BaseModel):
    data: List[StartupRead]
    meta: PaginationMeta


class InvestorListResponse(BaseModel):
    data: List[InvestorRead]
    meta: PaginationMeta


class InvestmentListResponse(BaseModel):
    data: List[InvestmentRead]
    meta: PaginationMeta


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

@app.get("/startups", response_model=StartupListResponse, tags=["Startups"])
def get_startups(
    page: int = Query(1, ge=1, description="Номер страницы (начиная с 1)"),
    per_page: int = Query(10, ge=1, le=100, description="Количество элементов на странице"),
    country: Optional[str] = Query(None, description="Фильтр по стране"),
    name: Optional[str] = Query(None, description="Поиск по названию (содержит)"),
    db: Session = Depends(get_db)
):
    """
    Получить список стартапов с пагинацией и фильтрацией
    
    ### Параметры:
    - **page**: Номер страницы (по умолчанию 1)
    - **per_page**: Количество элементов на странице (1-100, по умолчанию 10)
    - **country**: Фильтрация по стране (опционально)
    - **name**: Поиск по названию/части названия (опционально)
    """
    query = db.query(Startup)

    # Применяем фильтры
    if country:
        query = query.filter(Startup.country == country)
    if name:
        query = query.filter(Startup.name.ilike(f"%{name}%"))

    # Получаем общее количество
    total = query.count()

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
    startup = db.query(Startup).filter(Startup.id == startup_id).first()

    if not startup:
        raise HTTPException(status_code=404, detail=f"Startup with ID {startup_id} not found")

    return StartupRead.from_orm(startup)


# ==================== Investors Endpoints ====================

@app.get("/investors", response_model=InvestorListResponse, tags=["Investors"])
def get_investors(
    page: int = Query(1, ge=1, description="Номер страницы (начиная с 1)"),
    per_page: int = Query(10, ge=1, le=100, description="Количество элементов на странице"),
    name: Optional[str] = Query(None, description="Поиск по названию (содержит)"),
    db: Session = Depends(get_db)
):
    """
    Получить список инвесторов с пагинацией и фильтрацией
    
    ### Параметры:
    - **page**: Номер страницы (по умолчанию 1)
    - **per_page**: Количество элементов на странице (1-100, по умолчанию 10)
    - **name**: Поиск по названию/части названия (опционально)
    """
    query = db.query(Investor)

    # Применяем фильтры
    if name:
        query = query.filter(Investor.name.ilike(f"%{name}%"))

    # Получаем общее количество
    total = query.count()

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
    investor = db.query(Investor).filter(Investor.id == investor_id).first()

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
    db: Session = Depends(get_db)
):
    """
    Получить список инвестиций с пагинацией и фильтрацией
    
    ### Параметры:
    - **page**: Номер страницы (по умолчанию 1)
    - **per_page**: Количество элементов на странице (1-100, по умолчанию 10)
    - **startup_id**: Фильтр по ID стартапа (опционально)
    - **investor_id**: Фильтр по ID инвестора (опционально)
    - **round**: Фильтр по типу раунда (опционально)
    - **min_amount**: Минимальная сумма инвестиции (опционально)
    - **max_amount**: Максимальная сумма инвестиции (опционально)
    """
    query = db.query(Investment)

    # Применяем фильтры
    if startup_id:
        query = query.filter(Investment.startup_id == startup_id)
    if investor_id:
        query = query.filter(Investment.investor_id == investor_id)
    if round:
        query = query.filter(Investment.round == round)
    if min_amount is not None:
        query = query.filter(Investment.amount_usd >= min_amount)
    if max_amount is not None:
        query = query.filter(Investment.amount_usd <= max_amount)

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


# ==================== Statistics Endpoints ====================

@app.get("/statistics", tags=["Statistics"])
def get_statistics(db: Session = Depends(get_db)):
    """Получить общую статистику по БД"""
    from sqlalchemy import func

    # Общие подсчеты
    startup_count = db.query(Startup).count()
    investor_count = db.query(Investor).count()
    investment_count = db.query(Investment).count()

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

    return {
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
        ]
    }


# ==================== Error Handlers ====================

@app.exception_handler(HTTPException)
def http_exception_handler(request, exc):
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }
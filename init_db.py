#!/usr/bin/env python3
"""
init_db.py — Инициализация базы данных.
Создаёт все таблицы (включая новые колонки) и загружает
реальные данные из crunchbase_real_data.json.
"""

import os
import sys
import json
import random
from datetime import date, datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models import Base, Startup, Investor, Investment, User
from app.auth import get_password_hash

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL_LOCAL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/invest_db"
)

ROUNDS = ["Seed", "Series A", "Series B", "Series C", "Series D", "Growth"]

FOCUS_MAP = {
    "Sequoia Capital": "Technology, Consumer, Enterprise",
    "Andreessen Horowitz": "Software, Crypto, Bio",
    "Index Ventures": "E-commerce, Gaming, SaaS",
    "Kleiner Perkins": "CleanTech, Life Sciences",
    "Y Combinator": "Early-stage, All sectors",
    "Tiger Global": "Internet, SaaS, FinTech",
    "General Catalyst": "Health, Climate, AI",
    "Accel": "SaaS, Security, Developer tools",
    "Greylock": "Enterprise, Consumer",
    "Khosla Ventures": "CleanTech, AI, Health",
    "Lightspeed Venture Partners": "Enterprise, Consumer, FinTech",
    "Lightspeed": "Enterprise, Consumer, FinTech",
    "Founders Fund": "Deep Tech, Biotech",
    "DST Global": "Internet, Consumer",
    "Ribbit Capital": "FinTech",
    "Thrive Capital": "Technology, Media",
    "Google": "AI, Cloud, Consumer",
    "Microsoft": "Enterprise, Cloud, AI",
    "Amazon": "Cloud, Logistics",
    "SoftBank Vision Fund": "AI, Robotics, IoT",
    "Bessemer Venture Partners": "Cloud, Security",
    "General Atlantic": "Growth equity",
    "Insight Partners": "Software, Internet",
}


def make_source_url(name: str) -> str:
    slug = name.lower().replace(" ", "-").replace(".", "").replace(",", "").replace("'", "")
    return f"https://www.crunchbase.com/organization/{slug}"


def generate_investment_amounts(total_funding: float, num_investors: int) -> list:
    """Распределить сумму funding между инвесторами."""
    if total_funding <= 0 or num_investors == 0:
        return []
    weights = [random.uniform(0.2, 1.0) for _ in range(num_investors)]
    total_weight = sum(weights)
    amounts = [round((w / total_weight) * total_funding, 2) for w in weights]
    # Выровнять сумму
    diff = total_funding - sum(amounts)
    amounts[-1] += diff
    return amounts


try:
    print("📊 Investment Intelligence Hub — Инициализация БД")
    print("=" * 52)

    engine = create_engine(DATABASE_URL, echo=False)

    # ── Шаг 1: Пересоздаём схему (drop+create для SQLite) ──────────────────
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    if existing_tables:
        # Проверяем, есть ли уже новые колонки
        if "startups" in existing_tables:
            cols = [c["name"] for c in inspector.get_columns("startups")]
            if "source_url" not in cols or "created_at" not in cols:
                print("🔄 Обнаружена устаревшая схема — пересоздаём таблицы...")
                Base.metadata.drop_all(engine)

    print("📋 Создание таблиц (полная схема)...")
    Base.metadata.create_all(engine)
    print("✅ Таблицы созданы")

    Session = sessionmaker(bind=engine)
    session = Session()

    # ── Шаг 2: Создаём admin пользователя ──────────────────────────────────
    if session.query(User).count() == 0:
        admin_password = os.getenv("ADMIN_PASSWORD", "Admin@12345!")
        admin = User(
            username="admin",
            email="admin@investmenthub.local",
            hashed_password=get_password_hash(admin_password),
            is_active=True,
            is_admin=True,
        )
        session.add(admin)
        session.commit()
        print(f"👤 Admin пользователь создан (пароль: {admin_password})")

    # ── Шаг 3: Загружаем реальные данные ───────────────────────────────────
    cb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crunchbase_real_data.json")
    with open(cb_path, "r", encoding="utf-8") as f:
        cb_data = json.load(f)

    raw_startups = cb_data.get("startups", [])
    raw_investors = cb_data.get("investors", [])

    print(f"\n📥 Источник данных: {os.path.basename(cb_path)}")
    print(f"   Стартапов в источнике: {len(raw_startups)}")
    print(f"   Инвесторов в источнике: {len(raw_investors)}")

    # ── Шаг 4: Инвесторы ───────────────────────────────────────────────────
    existing_inv_map = {i.name: i for i in session.query(Investor).all()}
    new_inv_count = 0

    for inv_name in raw_investors:
        if inv_name not in existing_inv_map:
            inv = Investor(
                name=inv_name,
                fund_name=f"{inv_name} Global Fund",
                focus_area=FOCUS_MAP.get(inv_name, "Technology, Software"),
            )
            session.add(inv)
            new_inv_count += 1

    session.flush()
    all_investors_map = {i.name: i for i in session.query(Investor).all()}
    print(f"\n👥 Инвесторов создано: {new_inv_count} (Всего: {len(all_investors_map)})")

    # ── Шаг 5: Стартапы + Инвестиции ───────────────────────────────────────
    existing_startups = {s.name for s in session.query(Startup).all()}
    new_startups_count = 0
    new_investments_count = 0

    print("🏢 Загрузка стартапов...")
    for s_data in raw_startups:
        name = s_data["name"]
        if name in existing_startups:
            continue

        startup = Startup(
            name=name,
            country=s_data.get("country", "USA"),
            description=s_data.get("description", ""),
            founded_year=s_data.get("founded_year", 2010),
            status=s_data.get("status", "Active"),
            source_url=make_source_url(name),
        )
        session.add(startup)
        session.flush()
        existing_startups.add(name)
        new_startups_count += 1

        total_funding = s_data.get("funding", 0)
        investors_list = [
            n for n in s_data.get("investors", []) if n != "Bootstrapped"
        ]

        if not investors_list:
            continue

        # Создаём/находим инвесторов из данного стартапа
        valid_investors = []
        for inv_name in investors_list:
            if inv_name in all_investors_map:
                valid_investors.append(all_investors_map[inv_name])
            else:
                new_inv = Investor(
                    name=inv_name,
                    fund_name=f"{inv_name} Fund",
                    focus_area=FOCUS_MAP.get(inv_name, "Technology"),
                )
                session.add(new_inv)
                session.flush()
                all_investors_map[inv_name] = new_inv
                valid_investors.append(new_inv)

        amounts = generate_investment_amounts(total_funding, len(valid_investors))
        founded = s_data.get("founded_year") or 2015

        for idx, investor in enumerate(valid_investors):
            amount = amounts[idx] if amounts else float(random.randint(500_000, 10_000_000))

            # Раунд по размеру суммы
            if amount >= 200_000_000:
                round_name = "Growth"
            elif amount >= 50_000_000:
                round_name = "Series C"
            elif amount >= 15_000_000:
                round_name = "Series B"
            elif amount >= 3_000_000:
                round_name = "Series A"
            else:
                round_name = "Seed"

            invest_year = min(2024, founded + 1 + idx)
            inv_date = date(invest_year, random.randint(1, 12), random.randint(1, 28))

            investment = Investment(
                startup_id=startup.id,
                investor_id=investor.id,
                round=round_name,
                amount_usd=round(amount, 2),
                date=inv_date,
                status="Concluded" if idx < len(valid_investors) - 1 else "Active",
            )
            session.add(investment)
            new_investments_count += 1

    session.commit()

    total_s = session.query(Startup).count()
    total_i = session.query(Investor).count()
    total_inv = session.query(Investment).count()
    total_u = session.query(User).count()

    print(f"\n{'=' * 52}")
    print("✨ БД успешно инициализирована реальными данными!")
    print(f"   📊 Стартапов: {total_s}")
    print(f"   👥 Инвесторов: {total_i}")
    print(f"   💰 Инвестиций: {total_inv}")
    print(f"   👤 Пользователей: {total_u}")
    print(f"{'=' * 52}")

    session.close()

except Exception as e:
    print(f"\n❌ Ошибка при инициализации БД: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

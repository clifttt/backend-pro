#!/usr/bin/env python3
"""
Инициализация базы данных
Создание всех таблиц и загрузка тестовых данных
"""

import os
import sys
import random
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Убедимся что app модули доступны
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models import Base, Startup, Investor, Investment

load_dotenv()

# Получить DATABASE_URL
DATABASE_URL = os.getenv(
    "DATABASE_URL_LOCAL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/invest_db"
)

print(f"📊 Инициализация БД...")
print(f"🔗 Подключение к: {DATABASE_URL.replace('postgres', 'pg').split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")

try:
    # Создаем engine и session
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)

    # Создаем все таблицы
    print("📋 Создание таблиц...")
    Base.metadata.create_all(engine)
    print("✅ Таблицы созданы/обновлены")

    # Инициализируем данные
    session = Session()

    # Проверяем, нужно ли загружать тестовые данные
    existing_startups = session.query(Startup).count()

    if existing_startups == 0:
        print("📥 Загрузка тестовых данных...")

        # Примеры стартапов
        startups_data = [
            ("TechFlow", "USA"),
            ("GreenEnergy", "Canada"),
            ("AI-Core", "USA"),
            ("CyberShield", "UK"),
            ("FinPrime", "Singapore"),
            ("CloudStack", "USA"),
            ("DataVault", "Germany"),
            ("WebScale", "USA"),
            ("SecureNet", "Switzerland"),
            ("BioTech Pro", "USA"),
        ]

        # Примеры инвесторов
        investors_data = [
            "Sequoia Capital",
            "Y Combinator",
            "Tiger Global",
            "SoftBank",
            "Accel",
            "Andreessen Horowitz",
            "Kleiner Perkins",
            "First Round Capital",
            "Lightspeed Venture Partners",
            "General Catalyst",
        ]

        # Типы раундов
        rounds = ["Seed", "Series A", "Series B", "Series C", "Series D"]

        # Создаем стартапы
        startups = []
        for name, country in startups_data:
            startup = Startup(name=name, country=country)
            session.add(startup)
            startups.append(startup)

        session.flush()  # Получаем ID
        print(f"✅ Создано стартапов: {len(startups)}")

        # Создаем инвесторов
        investors = []
        for name in investors_data:
            investor = Investor(name=name)
            session.add(investor)
            investors.append(investor)

        session.flush()
        print(f"✅ Создано инвесторов: {len(investors)}")

        # Создаем инвестиции (связи)
        for startup in startups:
            # Каждый стартап получает 2-4 инвестиции
            num_investments = random.randint(2, 4)
            chosen_investors = random.sample(investors, num_investments)

            for idx, investor in enumerate(chosen_investors):
                investment = Investment(
                    startup_id=startup.id,
                    investor_id=investor.id,
                    round=rounds[idx % len(rounds)],
                    amount_usd=float(random.choice([100000, 250000, 500000, 1000000, 2500000, 5000000, 10000000])),
                    announced_date=None
                )
                session.add(investment)

        session.commit()
        print(f"✅ Создано инвестиций: {session.query(Investment).count()}")
        print("\n✨ БД инициализирована и заполнена тестовыми данными!")

    else:
        print(f"ℹ️  БД уже содержит данные:")
        print(f"   - Стартапов: {session.query(Startup).count()}")
        print(f"   - Инвесторов: {session.query(Investor).count()}")
        print(f"   - Инвестиций: {session.query(Investment).count()}")

    session.close()

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Инициализация завершена успешно!")
print("🚀 Вы можете запустить приложение: uvicorn app.main:app --reload")

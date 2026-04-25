#!/usr/bin/env python3
"""
Инициализация базы данных
Создание всех таблиц и загрузка РЕАЛЬНЫХ данных из crunchbase_real_data.json
"""

import os
import sys
import json
import random
from datetime import date
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models import Base, Startup, Investor, Investment

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL_LOCAL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/invest_db"
)

ROUNDS = ["Seed", "Series A", "Series B", "Series C", "Series D", "Venture Round"]

def load_crunchbase_data(filepath="crunchbase_real_data.json"):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_investment_rounds(total_funding, num_rounds):
    """Случайно распределяет общую сумму по n раундам."""
    if total_funding == 0 or num_rounds == 0:
        return []
        
    percentages = [random.uniform(0.1, 1.0) for _ in range(num_rounds)]
    total_weight = sum(percentages)
    
    rounds_amounts = []
    for p in percentages:
        amount = round((p / total_weight) * total_funding, 2)
        rounds_amounts.append(amount)
        
    # Корректируем последний раунд чтобы сумма сходилась идеально
    diff = total_funding - sum(rounds_amounts)
    rounds_amounts[-1] += diff
    
    # Сортируем: ранние раунды обычно меньше
    rounds_amounts.sort()
    return rounds_amounts

try:
    print(f"📊 Инициализация БД...")
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)

    print("📋 Создание таблиц...")
    Base.metadata.create_all(engine)
    print("✅ Таблицы созданы/обновлены")

    session = Session()

    # Загружаем реальные данные
    cb_data = load_crunchbase_data()
    raw_startups = cb_data.get("startups", [])
    raw_investors = cb_data.get("investors", [])
    
    # ─── 1. Инвесторы ───
    existing_investor_names = {i.name: i for i in session.query(Investor).all()}
    
    new_investors_count = 0
    for inv_name in raw_investors:
        if inv_name not in existing_investor_names:
            # Для реальных инвесторов мы просто сохраняем имя, фонд и фокус можно генерировать или оставить None
            inv = Investor(
                name=inv_name, 
                fund_name=f"{inv_name} Global Fund", 
                focus_area="Technology, Software"
            )
            session.add(inv)
            new_investors_count += 1
            
    session.flush()
    # Обновляем мапу
    all_investors_map = {i.name: i for i in session.query(Investor).all()}
    print(f"✅ Создано новых инвесторов: {new_investors_count} (Всего: {len(all_investors_map)})")

    # ─── 2. Стартапы и Инвестиции ───
    existing_startups = {s.name for s in session.query(Startup).all()}
    
    new_startups_count = 0
    new_investments_count = 0
    
    print("📥 Загрузка реальных стартапов и их раундов...")
    for s_data in raw_startups:
        name = s_data["name"]
        if name in existing_startups:
            continue
            
        startup = Startup(
            name=name,
            country=s_data.get("country", "USA"),
            description=s_data.get("description", ""),
            founded_year=s_data.get("founded_year", 2010),
            status=s_data.get("status", "Active")
        )
        session.add(startup)
        session.flush()
        existing_startups.add(name)
        new_startups_count += 1
        
        # Распределение раундов
        total_funding = s_data.get("funding", 0)
        investors_list = s_data.get("investors", [])
        
        if not investors_list or total_funding == 0:
            continue
            
        # Защита от несуществующих инвесторов (если в startups указан инвестор, которого нет в глобальном списке)
        valid_investors = []
        for inv_name in investors_list:
            if inv_name in all_investors_map:
                valid_investors.append(all_investors_map[inv_name])
            else:
                # На всякий случай создаем его
                new_inv = Investor(name=inv_name)
                session.add(new_inv)
                session.flush()
                all_investors_map[inv_name] = new_inv
                valid_investors.append(new_inv)
                
        num_rounds = len(valid_investors)
        rounds_amounts = generate_investment_rounds(total_funding, num_rounds)
        
        # Создаем инвестиции a16z -> Series A, Sequoia -> Series B и т.д.
        year = startup.founded_year
        for idx, amount in enumerate(rounds_amounts):
            investor = valid_investors[idx]
            
            # Логика: ранние раунды - ранние года, поздние - поздние
            year_offset = min(idx * 2, date.today().year - year)
            inv_date = date(year + year_offset, random.randint(1, 12), random.randint(1, 28))
            
            # Подбираем название раунда по индексу (Seed, Series A, B, C...)
            round_name = ROUNDS[min(idx, len(ROUNDS)-1)]
            
            investment = Investment(
                startup_id=startup.id,
                investor_id=investor.id,
                round=round_name,
                amount_usd=amount,
                date=inv_date,
                status="Concluded" if idx < len(rounds_amounts)-1 else "Active"
            )
            session.add(investment)
            new_investments_count += 1
            
    session.commit()

    total_startups = session.query(Startup).count()
    total_investments = session.query(Investment).count()

    print(f"\n✨ БД успешно заполнена реальными данными Crunchbase!")
    print(f"   📊 Создано стартапов: {new_startups_count}")
    print(f"   💰 Создано инвестиций: {new_investments_count}")
    print(f"   -----")
    print(f"   Всего стартапов: {total_startups}")
    print(f"   Всего инвесторов: {len(all_investors_map)}")
    print(f"   Всего инвестиций: {total_investments}")

    session.close()

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n🚀 Запуск приложения: uvicorn app.main:app --reload")

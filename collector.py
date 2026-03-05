import random
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from models import Base, Company, FundingRound, Investor, Investment

load_dotenv()

# Настройки подключения (PostgreSQL)
DATABASE_URL = os.getenv("DATABASE_URL_LOCAL", "postgresql+psycopg://postgres:postgres@localhost:5432/invest_db")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def run_collector():
    # 1. Создание таблиц
    Base.metadata.create_all(engine)
    
    # 2. Имитация сбора данных (Scraping/Parsing)
    # В реальном сценарии здесь будет requests.get() и BeautifulSoup
    print("Начало сбора данных...")
    
    names = ["TechFlow", "GreenEnergy", "AI-Core", "CyberShield", "FinPrime"]
    investor_names = ["Sequoia", "Y Combinator", "Tiger Global", "SoftBank", "Accel"]
    
    for i in range(55):  # Минимум 50 записей
        # Создаем компанию
        company = Company(name=f"{random.choice(names)} {i}", founded_date=None)
        session.add(company)
        session.flush() # Получаем ID компании
        
        # Создаем раунд финансирования
        f_round = FundingRound(
            company_id=company.id,
            round_type=random.choice(["Seed", "Series A", "Series B"]),
            amount=random.randint(100000, 10000000)
        )
        session.add(f_round)
        session.flush()
        
        # Создаем инвестора
        investor = Investor(
            name=f"{random.choice(investor_names)} Partners {i}",
            investor_type="VC"
        )
        session.add(investor)
        session.flush()
        
        # Создаем связь (Инвестиция)
        investment = Investment(
            round_id=f_round.id,
            investor_id=investor.id,
            is_lead=random.choice([True, False])
        )
        session.add(investment)

    session.commit()
    print(f"Успешно сохранено {session.query(Company).count()} записей.")

if __name__ == "__main__":
    run_collector()
#!/usr/bin/env python3
"""
Инициализация базы данных
Создание всех таблиц и загрузка тестовых данных (минимум 50 записей)
"""

import os
import sys
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

print(f"📊 Инициализация БД...")

STARTUPS_DATA = [
    ("TechFlow", "USA", "Enterprise workflow automation SaaS platform", 2018, "Active"),
    ("GreenEnergy", "Canada", "Renewable energy marketplace and analytics", 2019, "Active"),
    ("AI-Core", "USA", "AI-powered data analytics and insights platform", 2020, "Active"),
    ("CyberShield", "UK", "Next-generation cybersecurity solution", 2017, "Active"),
    ("FinPrime", "Singapore", "FinTech platform for cross-border payments", 2019, "Active"),
    ("CloudStack", "USA", "Cloud-native infrastructure management", 2016, "Acquired"),
    ("DataVault", "Germany", "Secure data warehousing and compliance", 2018, "Active"),
    ("WebScale", "USA", "Auto-scaling web infrastructure", 2015, "IPO"),
    ("SecureNet", "Switzerland", "Enterprise network security and monitoring", 2017, "Active"),
    ("BioTech Pro", "USA", "Pharmaceutical discovery acceleration with AI", 2020, "Active"),
    ("NeuralNet", "USA", "Deep learning model deployment platform", 2021, "Active"),
    ("QuantumLeap", "UK", "Quantum computing development tools", 2022, "Active"),
    ("AgriSmart", "Australia", "Precision farming intelligence platform", 2019, "Active"),
    ("ClimateAI", "France", "Climate risk modeling and analytics", 2020, "Active"),
    ("LogiChain", "Netherlands", "Supply chain optimization with ML", 2018, "Active"),
    ("MobiPay", "Singapore", "Mobile payment infrastructure", 2017, "Acquired"),
    ("EduTech", "USA", "Adaptive learning platform for K-12", 2019, "Active"),
    ("HealthBot", "USA", "AI-powered telemedicine diagnostics", 2020, "Active"),
    ("RoboTech", "Japan", "Industrial robotics automation", 2016, "Active"),
    ("OceanData", "Norway", "Ocean monitoring and analytics platform", 2021, "Active"),
    ("SpaceVentures", "USA", "Satellite data analytics", 2018, "Active"),
    ("CryptoVault", "Malta", "Institutional crypto custody solution", 2019, "Active"),
    ("TeleHealth", "USA", "Remote patient monitoring platform", 2020, "Active"),
    ("SkyDrone", "Israel", "Autonomous drone delivery network", 2019, "Active"),
    ("RealtyAI", "USA", "AI real estate valuation platform", 2018, "Active"),
    ("NanoTech", "Germany", "Nano-material research and production", 2017, "Active"),
    ("VoiceAI", "Canada", "Voice AI for enterprise customer service", 2020, "Active"),
    ("UniCloud", "USA", "Unified cloud management console", 2018, "Acquired"),
    ("PharmaX", "USA", "Drug discovery with generative AI", 2021, "Active"),
    ("BlockTrace", "UK", "Blockchain traceability for logistics", 2019, "Active"),
    ("SmartGrid", "Germany", "Intelligent energy grid management", 2018, "Active"),
    ("FoodTech", "Netherlands", "Alternative protein and food innovation", 2020, "Active"),
    ("InsurAI", "USA", "AI-driven insurance underwriting", 2019, "Active"),
    ("LegalBot", "UK", "Automated contract analysis platform", 2020, "Active"),
    ("TradeSmart", "Singapore", "Algorithmic trading infrastructure", 2018, "Active"),
    ("MediaAI", "USA", "AI-powered content generation platform", 2021, "Active"),
    ("RetailGenius", "USA", "Retail demand forecasting with ML", 2019, "Active"),
    ("CarbonZero", "Sweden", "Carbon credit marketplace", 2020, "Active"),
    ("NeuroLink", "USA", "Brain-computer interface research", 2022, "Active"),
    ("SafetyAI", "Germany", "Industrial safety monitoring with AI", 2019, "Active"),
    ("TravelTech", "France", "AI travel planning and optimization", 2018, "Active"),
    ("SportsAI", "USA", "Sports analytics and performance platform", 2020, "Active"),
    ("WaterTech", "Israel", "Smart water management platform", 2019, "Active"),
    ("AutoMind", "Germany", "Autonomous vehicle perception stack", 2018, "Active"),
    ("CloudSec", "USA", "Cloud-native security platform", 2020, "Active"),
    ("DataBridge", "UK", "Enterprise data integration platform", 2019, "Active"),
    ("FinanceAI", "USA", "AI financial planning assistant", 2021, "Active"),
    ("LocalPay", "Brazil", "Digital payments for emerging markets", 2020, "Active"),
    ("HRBot", "Canada", "AI HR and talent acquisition platform", 2019, "Active"),
    ("PropTech", "UK", "Commercial real estate intelligence", 2018, "Active"),
    ("LogAI", "USA", "Predictive log analysis for DevOps", 2021, "Active"),
    ("MarketMind", "USA", "AI-driven market research automation", 2020, "Active"),
    ("EcoTrack", "Sweden", "Corporate sustainability tracking", 2021, "Active"),
    ("BioScan", "USA", "Medical imaging AI diagnostics", 2019, "Active"),
    ("CityAI", "France", "Smart city infrastructure analytics", 2020, "Active"),
    ("SupplyML", "Germany", "ML-driven procurement optimization", 2019, "Active"),
    ("AeroTech Systems", "UK", "Aerospace predictive maintenance software", 2021, "Active"),
    ("MediCloud", "USA", "Cloud infrastructure for healthcare records", 2018, "Active"),
    ("QuantumSecure", "Switzerland", "Quantum-resistant encryption algorithms", 2020, "Active"),
    ("AgriData", "Netherlands", "IoT sensors for agricultural yield optimization", 2019, "Active"),
    ("VirtualMed", "Germany", "VR training for surgical procedures", 2022, "Active"),
    ("FinTech Next", "Singapore", "Decentralized finance lending platform", 2018, "Acquired"),
    ("NanoMed", "Israel", "Nanotechnology for targeted drug delivery", 2017, "Active"),
    ("AI-Law", "USA", "AI legal assistant for contract drafting", 2020, "Active"),
    ("GreenLogistics", "Sweden", "Zero-emission last-mile delivery software", 2021, "Active"),
    ("BioSynth", "USA", "Synthetic biology automation platform", 2019, "Active"),
    ("DataShield", "Canada", "Enterprise data privacy and compliance software", 2018, "Active"),
    ("AutoPilot", "USA", "AI co-pilot for software engineers", 2022, "Active"),
    ("SpaceRobotics", "Japan", "Robotics for satellite servicing and repair", 2020, "Active"),
    ("CryptoPay", "UK", "B2B crypto payment gateway", 2018, "Acquired"),
    ("EduAI", "India", "Personalized AI tutoring for STEM subjects", 2021, "Active"),
    ("HealthChain", "Switzerland", "Blockchain health record management", 2019, "Active"),
    ("RoboFarm", "Australia", "Autonomous agricultural robotics", 2017, "Active"),
    ("OceanClean", "Norway", "Automated ocean plastic removal systems", 2020, "Active"),
    ("AeroSpace Dynamics", "USA", "Next-gen propulsion systems modeling", 2021, "Active"),
    ("SecureCloud", "Germany", "End-to-end encrypted cloud storage", 2018, "Active"),
    ("TeleMed Plus", "USA", "Advanced remote patient diagnostics platform", 2020, "Active"),
    ("DroneDelivery", "Israel", "Urban drone delivery fleet management", 2019, "Active"),
    ("NeuroAI", "USA", "Brain-computer interface analytics", 2022, "Active"),
    ("SmartCity Tech", "France", "AI-driven traffic optimization", 2019, "Active"),
    ("FoodWaste Solutions", "Netherlands", "Supply chain waste reduction platform", 2021, "Active"),
    ("InsurTech Pro", "USA", "Parametric insurance risk modeling", 2020, "Active"),
    ("LegalAI", "UK", "Automated patent analysis and filing", 2018, "Active"),
    ("TradeFlow", "Singapore", "Cross-border trade finance automation", 2019, "Active"),
    ("MediaGen", "USA", "Generative AI for marketing copy", 2021, "Active"),
    ("RetailAnalytics", "USA", "In-store customer behavior tracking", 2018, "Active"),
    ("CarbonCapture", "Iceland", "Direct air capture technology optimization", 2020, "Active"),
    ("MindTech", "USA", "Digital therapeutics for mental health", 2021, "Active"),
    ("SafetyFirst", "Germany", "AI-powered workplace safety monitoring", 2019, "Active"),
    ("TravelAI", "Spain", "Personalized travel itinerary generation", 2022, "Active"),
    ("SportsAnalytics", "UK", "Player performance prediction models", 2018, "Active"),
    ("WaterTech Solutions", "Israel", "Leak detection and optimization for utilities", 2020, "Active"),
    ("AutoDrive", "Germany", "Simulation testing for autonomous driving", 2019, "Active"),
    ("CloudSecurity Pro", "USA", "Agentless cloud vulnerability scanning", 2021, "Active"),
    ("DataFlow", "Canada", "Real-time stream processing engine", 2018, "Active"),
    ("FinAI Assistants", "USA", "AI wealth management advisors", 2020, "Active"),
    ("LocalMarket", "Brazil", "B2B marketplace for local retailers", 2019, "Active"),
    ("HR Analytics", "USA", "Predictive employee retention modeling", 2021, "Active"),
    ("PropTech AI", "UK", "Automated building layout generation", 2022, "Active"),
    ("LogisticsAI", "Germany", "Dynamic routing optimization for fleets", 2018, "Active")
]

INVESTORS_DATA = [
    ("Sequoia Capital", "Sequoia Capital Fund XXI", "Technology, Consumer, Enterprise"),
    ("Y Combinator", "YC Batch Fund 2024", "Early-stage, All sectors"),
    ("Tiger Global", "Tiger Global PE XV", "Internet, SaaS, FinTech"),
    ("SoftBank Vision", "SoftBank Vision Fund 2", "AI, Robotics, IoT"),
    ("Accel Partners", "Accel Growth Fund VI", "SaaS, Security, Developer tools"),
    ("Andreessen Horowitz", "a16z Fund V", "Software, Crypto, Bio"),
    ("Kleiner Perkins", "KP Green Growth Fund", "CleanTech, Life Sciences"),
    ("First Round Capital", "First Round Fund XII", "Early-stage Startups"),
    ("Lightspeed Ventures", "Lightspeed Fund XI", "Enterprise, Consumer, FinTech"),
    ("General Catalyst", "GC Growth Fund III", "Health, Climate, AI"),
    ("Index Ventures", "Index Ventures X", "E-commerce, Gaming, SaaS"),
    ("Greylock Partners", "Greylock XVII", "Enterprise, Consumer"),
    ("Khosla Ventures", "KV Fund IX", "CleanTech, AI, Health"),
    ("GV (Google Ventures)", "GV 2024 Fund", "AI, Life Sciences"),
    ("NEA Partners", "NEA 17", "Healthcare, Technology"),
]

ROUNDS = ["Seed", "Series A", "Series B", "Series C", "Series D"]


try:
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)

    print("📋 Создание таблиц...")
    Base.metadata.create_all(engine)
    print("✅ Таблицы созданы/обновлены")

    session = Session()

    # ─── Investors ───
    existing_investors = {i.name for i in session.query(Investor).all()}
    investors = []
    for name, fund, focus in INVESTORS_DATA:
        if name not in existing_investors:
            inv = Investor(name=name, fund_name=fund, focus_area=focus)
            session.add(inv)
            investors.append(inv)
    session.flush()
    all_investors = session.query(Investor).all()
    print(f"✅ Инвесторов в БД: {len(all_investors)}")

    # ─── Startups & Investments ───
    existing_startups = {s.name for s in session.query(Startup).all()}

    if len(existing_startups) < 50:
        print("📥 Загрузка стартапов и инвестиций...")
        created = 0
        for name, country, desc, year, status in STARTUPS_DATA:
            if name in existing_startups:
                continue

            startup = Startup(
                name=name,
                country=country,
                description=desc,
                founded_year=year,
                status=status,
            )
            session.add(startup)
            session.flush()
            existing_startups.add(name)

            # 1–3 инвестиции на стартап
            num_inv = random.randint(1, 3)
            chosen = random.sample(all_investors, min(num_inv, len(all_investors)))
            inv_date = date(year + random.randint(0, 3), random.randint(1, 12), random.randint(1, 28))

            for investor in chosen:
                investment = Investment(
                    startup_id=startup.id,
                    investor_id=investor.id,
                    round=random.choice(ROUNDS),
                    amount_usd=float(random.choice([
                        150_000, 500_000, 1_000_000, 2_500_000,
                        5_000_000, 10_000_000, 25_000_000, 50_000_000
                    ])),
                    date=inv_date,
                    status=random.choice(["Active", "Concluded"]),
                )
                session.add(investment)
            created += 1

        session.commit()

        total_startups = session.query(Startup).count()
        total_investors = session.query(Investor).count()
        total_investments = session.query(Investment).count()

        print(f"✅ Создано новых стартапов: {created}")
        print(f"\n✨ БД инициализирована!")
        print(f"   📊 Стартапов: {total_startups}")
        print(f"   👥 Инвесторов: {total_investors}")
        print(f"   💰 Инвестиций: {total_investments}")

    else:
        total_startups = session.query(Startup).count()
        total_investors = session.query(Investor).count()
        total_investments = session.query(Investment).count()
        print(f"ℹ️  БД уже содержит данные:")
        print(f"   📊 Стартапов: {total_startups}")
        print(f"   👥 Инвесторов: {total_investors}")
        print(f"   💰 Инвестиций: {total_investments}")

    session.close()

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n✅ Инициализация завершена успешно!")
print("🚀 Запуск приложения: uvicorn app.main:app --reload")
print("📖 Swagger UI: http://localhost:8000/docs")

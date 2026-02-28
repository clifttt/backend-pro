import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Use DATABASE_URL_LOCAL for local development, DATABASE_URL for Docker
DATABASE_URL = os.getenv(
    "DATABASE_URL_LOCAL", 
    "postgresql+psycopg://postgres:postgres@localhost:5432/invest_db"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """Dependency для получения БД сессии"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

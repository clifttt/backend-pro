from sqlalchemy import Column, Integer, String, BigInteger, Boolean, ForeignKey, Date
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    founded_date = Column(Date)
    # Связь с раундами
    rounds = relationship("FundingRound", back_populates="company")

class FundingRound(Base):
    __tablename__ = "funding_rounds"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    round_type = Column(String) # Тип_раунда [cite: 13]
    amount = Column(BigInteger) # Сумма [cite: 14]
    
    company = relationship("Company", back_populates="rounds")
    investments = relationship("Investment", back_populates="funding_round")

class Investor(Base):
    __tablename__ = "investors"
    id = Column(Integer, primary_key=True)
    name = Column(String) # Название [cite: 20]
    investor_type = Column(String) # Тип [cite: 21]
    
    investments = relationship("Investment", back_populates="investor")

class Investment(Base):
    __tablename__ = "investments"
    round_id = Column(Integer, ForeignKey("funding_rounds.id"), primary_key=True)
    investor_id = Column(Integer, ForeignKey("investors.id"), primary_key=True)
    is_lead = Column(Boolean, default=False) # Лид_инвестор [cite: 19]

    funding_round = relationship("FundingRound", back_populates="investments")
    investor = relationship("Investor", back_populates="investments")
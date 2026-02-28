"""
Data Normalizer & Cleaner - Обработка и Бизнес-логика
Реализация модуля очистки и нормализации данных
Выделение сущностей (даты, имена, теги)
"""

import re
import logging
from typing import Optional, List, Tuple, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from models import Company, FundingRound, Investor, Investment

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Выделение сущностей из текста"""
    
    @staticmethod
    def extract_dates(text: str) -> List[str]:
        """Извлечь даты из текста"""
        if not text:
            return []
        
        patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{1,2}/\d{1,2}/\d{4}',  # MM/DD/YYYY
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',  # Full date
        ]
        
        dates = []
        for pattern in patterns:
            found = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(found)
        
        return list(set(dates))  # Убрать дубликаты
    
    @staticmethod
    def extract_names(text: str) -> List[str]:
        """Извлечь имена людей из текста"""
        if not text:
            return []
        
        # Простой паттерн для имён (слово с заглавной буквы)
        pattern = r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b'
        names = re.findall(pattern, text)
        
        return list(set(names))
    
    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """Извлечь числовые значения (для сумм финансирования)"""
        if not text:
            return []
        
        pattern = r'\$?[\d,]+(?:\.\d{2})?[\s]?(million|billion|thousand|M|B|K)?'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        numbers = []
        for match in matches:
            try:
                # Преобразовать в число
                if isinstance(match, tuple):
                    num_str = match[0]
                    multiplier = match[1] if match[1] else ""
                else:
                    num_str = match
                    multiplier = ""
                
                num = float(num_str.replace(',', '').replace('$', ''))
                
                # Применить множитель
                if multiplier.lower() in ['billion', 'b']:
                    num *= 1_000_000_000
                elif multiplier.lower() in ['million', 'm']:
                    num *= 1_000_000
                elif multiplier.lower() in ['thousand', 'k']:
                    num *= 1_000
                
                numbers.append(num)
            except ValueError:
                continue
        
        return numbers


class DataNormalizer:
    """Нормализация данных"""
    
    @staticmethod
    def normalize_company_name(name: str) -> str:
        """Нормализовать имя компании"""
        if not name:
            return ""
        
        # Удалить лишние пробелы
        name = re.sub(r'\s+', ' ', name).strip()
        
        # Привести к стандартному формату
        name = name.title()
        
        # Удалить специальные символы
        name = re.sub(r'[^\w\s\-\&\.]', '', name)
        
        return name
    
    @staticmethod
    def normalize_investor_name(name: str) -> str:
        """Нормализовать имя инвестора"""
        if not name:
            return ""
        
        name = re.sub(r'\s+', ' ', name).strip()
        name = name.title()
        
        # Удалить "Partners", "LLC", "Inc" и аналогично
        name = re.sub(r'\b(Partners?|LLC|Inc|Ltd|Corp|Ventures?|Capital|Funds?)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    @staticmethod
    def normalize_funding_amount(amount: int) -> int:
        """Нормализовать сумму финансирования"""
        if not isinstance(amount, (int, float)):
            return 0
        
        # Убедиться что значение в правильном диапазоне
        amount = max(0, int(amount))
        
        return amount
    
    @staticmethod
    def normalize_round_type(round_type: str) -> str:
        """Нормализовать тип раунда"""
        if not round_type:
            return "Unknown"
        
        round_type = round_type.strip().upper()
        
        # Стандартные типы раундов
        valid_types = ["SEED", "SERIES A", "SERIES B", "SERIES C", "SERIES D", "SERIES E", "IPO"]
        
        for valid in valid_types:
            if valid in round_type:
                return valid
        
        return "Unknown"


class QualityAssessment:
    """Оценка качества структурированных данных"""
    
    @staticmethod
    def assess_data_quality(session: Session) -> Dict[str, any]:
        """Оценить качество данных в БД"""
        logger.info("📊 Начало оценки качества данных...")
        
        try:
            # Счетчики
            total_companies = session.query(Company).count()
            total_rounds = session.query(FundingRound).count()
            total_investors = session.query(Investor).count()
            total_investments = session.query(Investment).count()
            
            # Проверка целостности
            companies_with_rounds = session.query(Company).filter(
                Company.rounds.any()
            ).count()
            
            rounds_with_investments = session.query(FundingRound).filter(
                FundingRound.investments.any()
            ).count()
            
            # Проверка валидности сумм
            valid_funding_rounds = session.query(FundingRound).filter(
                FundingRound.amount > 0
            ).count()
            
            # Проверка заполненности дат
            companies_with_dates = session.query(Company).filter(
                Company.founded_date.isnot(None)
            ).count()
            
            # Подсчет уникальных инвесторов и типов раундов
            unique_round_types = len(set(
                r[0] for r in session.query(FundingRound.round_type).distinct()
            ))
            unique_investor_types = len(set(
                i[0] for i in session.query(Investor.investor_type).distinct()
            ))
            
            # Итоговая оценка
            quality_score = 0.0
            quality_checks = []
            
            # Проверка 1: Достаточное количество записей
            if total_companies >= 50:
                quality_score += 25
                quality_checks.append("✅ Достаточное количество компаний (>50)")
            else:
                quality_checks.append(f"⚠️ Мало компаний ({total_companies})")
            
            # Проверка 2: Целостность данных
            referential_integrity = (companies_with_rounds / max(total_companies, 1)) * 100
            if referential_integrity >= 80:
                quality_score += 25
                quality_checks.append(f"✅ Хорошая целостность данных ({referential_integrity:.1f}%)")
            else:
                quality_checks.append(f"⚠️ Низкая целостность данных ({referential_integrity:.1f}%)")
            
            # Проверка 3: Валидность финансовых данных
            if valid_funding_rounds == total_rounds:
                quality_score += 25
                quality_checks.append("✅ Все суммы финансирования валидны")
            else:
                quality_checks.append(f"⚠️ Невалидные суммы ({total_rounds - valid_funding_rounds})")
            
            # Проверка 4: Разнообразие данных
            if unique_round_types >= 3 and unique_investor_types >= 3:
                quality_score += 25
                quality_checks.append(f"✅ Хорошее разнообразие (Типов раундов: {unique_round_types}, Типов инвесторов: {unique_investor_types})")
            else:
                quality_checks.append(f"⚠️ Низкое разнообразие")
            
            result = {
                "quality_score": quality_score,
                "total_companies": total_companies,
                "total_funding_rounds": total_rounds,
                "total_investors": total_investors,
                "total_investments": total_investments,
                "companies_with_rounds": companies_with_rounds,
                "rounds_with_investments": rounds_with_investments,
                "valid_funding_amounts": valid_funding_rounds,
                "companies_with_dates": companies_with_dates,
                "unique_round_types": unique_round_types,
                "unique_investor_types": unique_investor_types,
                "referential_integrity_percent": referential_integrity,
                "quality_checks": quality_checks,
                "assessment_timestamp": datetime.now().isoformat()
            }
            
            # Логирование результатов
            logger.info(f"📊 Результаты оценки качества:")
            logger.info(f"  🏢 Компаний: {total_companies}")
            logger.info(f"  💰 Раундов финансирования: {total_rounds}")
            logger.info(f"  👥 Инвесторов: {total_investors}")
            logger.info(f"  🔗 Связей: {total_investments}")
            logger.info(f"  ⭐ Оценка качества: {quality_score}/100")
            
            for check in quality_checks:
                logger.info(f"  {check}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка при оценке качества: {e}")
            return {"error": str(e)}


class DataProcessor:
    """Главный процессор данных"""
    
    def __init__(self, session: Session):
        self.session = session
        self.extractor = EntityExtractor()
        self.normalizer = DataNormalizer()
        self.quality_assessment = QualityAssessment()
    
    def process_all_data(self) -> None:
        """Обработать все данные в БД"""
        logger.info("🔄 Начало полной обработки данных...")
        
        try:
            # Нормализовать компании
            companies = self.session.query(Company).all()
            for company in companies:
                company.name = self.normalizer.normalize_company_name(company.name)
            
            # Нормализовать инвесторов
            investors = self.session.query(Investor).all()
            for investor in investors:
                investor.name = self.normalizer.normalize_investor_name(investor.name)
                if not investor.investor_type:
                    investor.investor_type = "VC"  # Значение по умолчанию
            
            # Нормализовать раунды финансирования
            rounds = self.session.query(FundingRound).all()
            for round_data in rounds:
                round_data.round_type = self.normalizer.normalize_round_type(round_data.round_type)
                round_data.amount = self.normalizer.normalize_funding_amount(round_data.amount)
            
            self.session.commit()
            logger.info("✅ Нормализация завершена")
            
            # Оценить качество
            assessment = self.quality_assessment.assess_data_quality(self.session)
            return assessment
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Ошибка при обработке данных: {e}")
            raise
        finally:
            self.session.close()


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models import Base
    
    load_dotenv()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    DATABASE_URL = os.getenv("DATABASE_URL_LOCAL", "postgresql+psycopg://postgres:postgres@localhost:5432/invest_db")
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    
    Base.metadata.create_all(engine)
    
    session = Session()
    processor = DataProcessor(session)
    result = processor.process_all_data()
    
    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ ОБРАБОТКИ И ОЦЕНКИ КАЧЕСТВА")
    print("="*60)
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))

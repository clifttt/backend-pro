"""
Data Normalizer & Cleaner — Обработка и Бизнес-логика
Реализация модуля очистки и нормализации данных.
Выделение сущностей (даты, имена, теги).
"""

import re
import logging
import os
import sys
from typing import Optional, List, Dict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.models import Startup, Investor, Investment

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
#  Entity Extractor
# ─────────────────────────────────────────────────────────

class EntityExtractor:
    """Выделение сущностей из текста"""

    @staticmethod
    def extract_dates(text: str) -> List[str]:
        """Извлечь даты из текста"""
        if not text:
            return []
        patterns = [
            r'\d{4}-\d{2}-\d{2}',
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
        ]
        dates = []
        for pattern in patterns:
            dates.extend(re.findall(pattern, text, re.IGNORECASE))
        return list(set(dates))

    @staticmethod
    def extract_names(text: str) -> List[str]:
        """Извлечь имена людей из текста (простой паттерн)"""
        if not text:
            return []
        pattern = r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b'
        return list(set(re.findall(pattern, text)))

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
                num_str, multiplier = (match if isinstance(match, tuple) else (match, ""))
                num = float(str(num_str).replace(',', '').replace('$', ''))
                if multiplier.lower() in ['billion', 'b']:
                    num *= 1_000_000_000
                elif multiplier.lower() in ['million', 'm']:
                    num *= 1_000_000
                elif multiplier.lower() in ['thousand', 'k']:
                    num *= 1_000
                numbers.append(num)
            except (ValueError, AttributeError):
                continue
        return numbers

    @staticmethod
    def extract_tags(text: str) -> List[str]:
        """Извлечь технологические теги из текста"""
        if not text:
            return []
        tech_keywords = [
            'AI', 'ML', 'SaaS', 'FinTech', 'HealthTech', 'EdTech', 'IoT',
            'Blockchain', 'Cloud', 'Data', 'Security', 'Platform', 'Analytics'
        ]
        found = []
        for kw in tech_keywords:
            if kw.lower() in text.lower():
                found.append(kw)
        return found


# ─────────────────────────────────────────────────────────
#  Data Normalizer
# ─────────────────────────────────────────────────────────

class DataNormalizer:
    """Нормализация данных"""

    @staticmethod
    def normalize_company_name(name: str) -> str:
        """Нормализовать имя компании"""
        if not name:
            return ""
        name = re.sub(r'\s+', ' ', name).strip()
        name = re.sub(r'[^\w\s\-&\.]', '', name)
        return name

    @staticmethod
    def normalize_investor_name(name: str) -> str:
        """Нормализовать имя инвестора"""
        if not name:
            return ""
        name = re.sub(r'\s+', ' ', name).strip()
        return name

    @staticmethod
    def normalize_funding_amount(amount) -> float:
        """Нормализовать сумму финансирования"""
        try:
            return max(0.0, float(amount))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def normalize_round_type(round_type: str) -> str:
        """Нормализовать тип раунда"""
        if not round_type:
            return "Unknown"
        rt = round_type.strip().upper()
        valid = ["SEED", "SERIES A", "SERIES B", "SERIES C", "SERIES D", "SERIES E", "IPO"]
        for v in valid:
            if v in rt:
                return v.title()
        return round_type.strip().title()

    @staticmethod
    def normalize_status(status: str) -> str:
        """Нормализовать статус"""
        if not status:
            return "Unknown"
        mapping = {
            "active": "Active",
            "acquired": "Acquired",
            "ipo": "IPO",
            "closed": "Closed",
            "concluded": "Concluded",
        }
        return mapping.get(status.lower(), status.strip().title())


# ─────────────────────────────────────────────────────────
#  Quality Assessment
# ─────────────────────────────────────────────────────────

class QualityAssessment:
    """Оценка качества структурированных данных"""

    @staticmethod
    def assess_data_quality(session: Session) -> Dict:
        """Оценить качество данных в БД"""
        logger.info("📊 Начало оценки качества данных...")

        try:
            total_startups = session.query(Startup).count()
            total_investors = session.query(Investor).count()
            total_investments = session.query(Investment).count()

            startups_with_desc = session.query(Startup).filter(
                Startup.description.isnot(None)
            ).count()

            startups_with_year = session.query(Startup).filter(
                Startup.founded_year.isnot(None)
            ).count()

            investments_with_amount = session.query(Investment).filter(
                Investment.amount_usd > 0
            ).count()

            quality_score = 0.0
            quality_checks = []

            # Проверка 1: Количество стартапов ≥ 50
            if total_startups >= 50:
                quality_score += 25
                quality_checks.append(f"✅ Достаточно стартапов ({total_startups} ≥ 50)")
            else:
                quality_checks.append(f"⚠️ Мало стартапов ({total_startups} < 50)")

            # Проверка 2: Наличие описаний
            desc_pct = (startups_with_desc / max(total_startups, 1)) * 100
            if desc_pct >= 80:
                quality_score += 25
                quality_checks.append(f"✅ Описания заполнены ({desc_pct:.1f}%)")
            else:
                quality_checks.append(f"⚠️ Мало описаний ({desc_pct:.1f}%)")

            # Проверка 3: Суммы финансирования
            amount_pct = (investments_with_amount / max(total_investments, 1)) * 100
            if amount_pct >= 90:
                quality_score += 25
                quality_checks.append(f"✅ Суммы финансирования валидны ({amount_pct:.1f}%)")
            else:
                quality_checks.append(f"⚠️ Невалидные суммы ({100 - amount_pct:.1f}%)")

            # Проверка 4: Инвесторы и инвестиции
            if total_investors >= 10 and total_investments >= 30:
                quality_score += 25
                quality_checks.append(f"✅ Инвесторов: {total_investors}, Инвестиций: {total_investments}")
            else:
                quality_checks.append(f"⚠️ Инвесторов: {total_investors}, Инвестиций: {total_investments}")

            result = {
                "quality_score": quality_score,
                "total_startups": total_startups,
                "total_investors": total_investors,
                "total_investments": total_investments,
                "startups_with_description": startups_with_desc,
                "startups_with_year": startups_with_year,
                "valid_investment_amounts": investments_with_amount,
                "quality_checks": quality_checks,
                "assessment_timestamp": datetime.now().isoformat()
            }

            logger.info(f"⭐ Оценка качества: {quality_score}/100")
            for check in quality_checks:
                logger.info(f"   {check}")

            return result

        except Exception as e:
            logger.error(f"❌ Ошибка при оценке качества: {e}")
            return {"error": str(e)}


# ─────────────────────────────────────────────────────────
#  Data Processor
# ─────────────────────────────────────────────────────────

class DataProcessor:
    """Главный процессор данных"""

    def __init__(self, session: Session):
        self.session = session
        self.extractor = EntityExtractor()
        self.normalizer = DataNormalizer()
        self.quality = QualityAssessment()

    def process_all_data(self) -> Dict:
        """Обработать все данные в БД"""
        logger.info("🔄 Начало полной обработки данных...")

        try:
            # Нормализовать стартапы
            startups = self.session.query(Startup).all()
            for startup in startups:
                startup.name = self.normalizer.normalize_company_name(startup.name)
                if startup.status:
                    startup.status = self.normalizer.normalize_status(startup.status)

            # Нормализовать инвесторов
            investors = self.session.query(Investor).all()
            for investor in investors:
                investor.name = self.normalizer.normalize_investor_name(investor.name)

            # Нормализовать инвестиции
            investments = self.session.query(Investment).all()
            for inv in investments:
                if inv.round:
                    inv.round = self.normalizer.normalize_round_type(inv.round)
                if inv.amount_usd is not None:
                    inv.amount_usd = self.normalizer.normalize_funding_amount(inv.amount_usd)
                if inv.status:
                    inv.status = self.normalizer.normalize_status(inv.status)

            self.session.commit()
            logger.info("✅ Нормализация завершена")

            # Оценить качество
            return self.quality.assess_data_quality(self.session)

        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Ошибка при обработке данных: {e}", exc_info=True)
            raise
        finally:
            self.session.close()


# ─────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json
    from dotenv import load_dotenv
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models import Base

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    DATABASE_URL = os.getenv(
        "DATABASE_URL_LOCAL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/invest_db"
    )
    _engine = create_engine(DATABASE_URL)
    _Session = sessionmaker(bind=_engine)

    Base.metadata.create_all(_engine)

    session = _Session()
    processor = DataProcessor(session)
    result = processor.process_all_data()

    print("\n" + "="*60)
    print("РЕЗУЛЬТАТЫ ОБРАБОТКИ И ОЦЕНКИ КАЧЕСТВА")
    print("="*60)
    print(json.dumps(result, indent=2, ensure_ascii=False))

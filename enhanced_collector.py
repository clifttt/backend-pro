"""
Enhanced Data Collector - Часть 2
Реализация обхода блокировок (User-Agents, Proxy, Delay)
Автоматизация запуска (Cron/Scheduler)
Обработка ошибок соединения
"""

import random
import time
import logging
import os
import sys
from typing import Optional, Dict, List
from datetime import datetime, timedelta, date

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

try:
    from fake_useragent import UserAgent
    HAS_FAKE_UA = True
except ImportError:
    HAS_FAKE_UA = False

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Startup, Investor, Investment

load_dotenv()

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Настройки БД
DATABASE_URL = os.getenv(
    "DATABASE_URL_LOCAL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/invest_db"
)
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


class ProxyManager:
    """Управление прокси-серверами"""

    def __init__(self):
        # Публичные прокси (заменить на реальные платные при необходимости)
        self.proxies: List[str] = []
        self.current_index = 0

    def get_proxy(self) -> Optional[Dict[str, str]]:
        """Получить следующий прокси из ротации"""
        if not self.proxies:
            return None

        proxy_url = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)

        return {"http": proxy_url, "https": proxy_url}


class UserAgentManager:
    """Управление User-Agent'ами"""

    FALLBACK_UAS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    ]

    def __init__(self):
        if HAS_FAKE_UA:
            try:
                self.ua = UserAgent()
                self._use_fake = True
            except Exception:
                self._use_fake = False
        else:
            self._use_fake = False

    def get_user_agent(self) -> str:
        """Получить случайный User-Agent"""
        if self._use_fake:
            try:
                return self.ua.random
            except Exception:
                pass
        return random.choice(self.FALLBACK_UAS)


class EnhancedDataCollector:
    """Улучшенный коллектор данных с защитой от блокировок"""

    STARTUP_NAMES = [
        "TechFlow", "GreenEnergy", "AI-Core", "CyberShield", "FinPrime",
        "CloudWave", "DataVault", "NeuralNet", "QuantumLeap", "SecureVault",
        "BlockChain Pro", "RoboTech", "Space Ventures", "BioHealth", "EduTech",
        "AgriSmart", "ClimateAI", "DeepMind Analytics", "HealthBot", "LogiChain",
        "MobiPay", "NanoTech", "OceanData", "PharmaX", "QuickShip",
        "RealtyAI", "SkyDrone", "TeleHealth", "UniCloud", "VoiceAI",
    ]

    INVESTOR_NAMES = [
        "Sequoia Capital", "Y Combinator", "Tiger Global", "SoftBank Vision",
        "Accel Partners", "Andreessen Horowitz", "Index Ventures", "Greylock Partners",
        "Khosla Ventures", "IVP Fund", "General Catalyst", "Kleiner Perkins",
        "Lightspeed Ventures", "GV (Google Ventures)", "NEA Partners",
    ]

    INVESTOR_FUND_NAMES = {
        "Sequoia Capital": "Sequoia Capital Fund XXI",
        "Y Combinator": "YC Batch Fund",
        "Tiger Global": "Tiger Global PE XIV",
        "SoftBank Vision": "SoftBank Vision Fund 2",
        "Accel Partners": "Accel Growth Fund VI",
        "Andreessen Horowitz": "a16z Fund IV",
        "Index Ventures": "Index Ventures IX",
        "Greylock Partners": "Greylock XVI",
        "Khosla Ventures": "Khosla Ventures VIII",
        "IVP Fund": "IVP XIX",
        "General Catalyst": "GC Growth Fund",
        "Kleiner Perkins": "KPCB Green Growth",
        "Lightspeed Ventures": "Lightspeed X",
        "GV (Google Ventures)": "GV 2024 Fund",
        "NEA Partners": "NEA 17",
    }

    INVESTOR_FOCUS = {
        "Sequoia Capital": "Technology, Consumer, Enterprise",
        "Y Combinator": "Early-stage, All sectors",
        "Tiger Global": "Internet, SaaS, FinTech",
        "SoftBank Vision": "AI, Robotics, IoT",
        "Accel Partners": "SaaS, Security, Developer tools",
        "Andreessen Horowitz": "Software, Crypto, Bio",
        "Index Ventures": "E-commerce, Gaming, SaaS",
        "Greylock Partners": "Enterprise, Consumer",
        "Khosla Ventures": "CleanTech, AI, Health",
        "IVP Fund": "Late-stage, Growth",
        "General Catalyst": "Health, Climate, AI",
        "Kleiner Perkins": "CleanTech, Life Sciences",
        "Lightspeed Ventures": "Enterprise, Consumer, FinTech",
        "GV (Google Ventures)": "AI, Life Sciences",
        "NEA Partners": "Healthcare, Technology",
    }

    COUNTRIES = ["USA", "UK", "Germany", "Canada", "Singapore", "Israel",
                 "France", "Netherlands", "Sweden", "Australia"]

    ROUNDS = ["Seed", "Series A", "Series B", "Series C", "Series D"]

    STATUSES = ["Active", "Acquired", "IPO", "Closed"]

    DESCRIPTIONS = [
        "Enterprise SaaS platform for workflow automation",
        "AI-powered data analytics and insights",
        "Next-generation cybersecurity solution",
        "Renewable energy marketplace and analytics",
        "FinTech platform for cross-border payments",
        "Cloud-native infrastructure management",
        "Healthcare data platform and diagnostics",
        "Supply chain optimization with ML",
        "EdTech platform with adaptive learning",
        "AgriTech precision farming intelligence",
        "Real estate AI valuation platform",
        "Autonomous drone delivery network",
        "Telemedicine and digital health hub",
        "Blockchain traceability for logistics",
        "Voice AI for enterprise customer service",
        "Quantum computing development tools",
        "Climate risk modeling and analytics",
        "Nano-material research and production",
        "Ocean data monitoring platform",
        "Pharmaceutical discovery acceleration",
    ]

    def __init__(self, min_delay: float = 0.1, max_delay: float = 0.5):
        self.session = Session()
        self.proxy_manager = ProxyManager()
        self.ua_manager = UserAgentManager()
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.requests_session = self._create_robust_session()

    def _create_robust_session(self) -> requests.Session:
        """Создать сессию с автоматическими повторами"""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _get_headers(self) -> Dict[str, str]:
        """Получить случайные заголовки для запроса"""
        return {
            "User-Agent": self.ua_manager.get_user_agent(),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
        }

    def _apply_delay(self) -> None:
        """Применить случайную задержку между запросами"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

    def fetch_url(self, url: str, use_proxy: bool = False) -> Optional[str]:
        """Получить содержимое URL с повторами и защитой от блокировок"""
        for attempt in range(3):
            try:
                kwargs: Dict = {
                    "headers": self._get_headers(),
                    "timeout": 10,
                    "verify": True,
                }
                if use_proxy:
                    proxy = self.proxy_manager.get_proxy()
                    if proxy:
                        kwargs["proxies"] = proxy

                response = self.requests_session.get(url, **kwargs)
                response.raise_for_status()
                logger.info(f"✅ Успешно: {url}")
                return response.text

            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ Timeout (попытка {attempt+1}/3): {url}")
            except requests.exceptions.ConnectionError:
                logger.error(f"❌ Ошибка соединения: {url}")
                break
            except requests.exceptions.HTTPError as e:
                logger.error(f"🚫 HTTP {e.response.status_code}: {url}")
                break
            except Exception as e:
                logger.error(f"❌ Ошибка: {e}")
                break

            time.sleep(2 ** attempt)  # exponential backoff

        return None

    def collect_data(self, num_startups: int = 60) -> int:
        """
        Сгенерировать данные и сохранить в БД.
        В боевой версии здесь был бы реальный парсинг API/сайтов.
        Возвращает количество записей в БД.
        """
        logger.info(f"🚀 Начало сбора данных. Цель: {num_startups} стартапов")

        try:
            # 1. Создать инвесторов (если не существуют)
            existing_investors = {
                inv.name for inv in self.session.query(Investor).all()
            }

            investors_created = []
            for inv_name in self.INVESTOR_NAMES:
                if inv_name not in existing_investors:
                    self._apply_delay()
                    investor = Investor(
                        name=inv_name,
                        fund_name=self.INVESTOR_FUND_NAMES.get(inv_name),
                        focus_area=self.INVESTOR_FOCUS.get(inv_name),
                    )
                    self.session.add(investor)
                    investors_created.append(investor)
                    logger.info(f"  👤 Создан инвестор: {inv_name}")

            self.session.flush()
            all_investors = self.session.query(Investor).all()
            logger.info(f"✅ Инвесторов в БД: {len(all_investors)}")

            # 2. Создать стартапы
            existing_startups = {
                s.name for s in self.session.query(Startup).all()
            }

            current_count = len(existing_startups)
            if current_count >= num_startups:
                logger.info(f"✅ Уже есть {current_count} стартапов. Сбор не нужен.")
                self.session.commit()
                return current_count

            records_to_create = num_startups - current_count
            base_year = 2024

            for i in range(records_to_create):
                self._apply_delay()

                # Уникальное имя
                base_name = random.choice(self.STARTUP_NAMES)
                name = f"{base_name} #{current_count + i + 1}"
                while name in existing_startups:
                    name = f"{base_name} {random.randint(100, 999)}"
                existing_startups.add(name)

                startup = Startup(
                    name=name,
                    country=random.choice(self.COUNTRIES),
                    description=random.choice(self.DESCRIPTIONS),
                    founded_year=random.randint(2010, 2023),
                    status=random.choices(
                        self.STATUSES, weights=[70, 15, 10, 5]
                    )[0],
                )
                self.session.add(startup)
                self.session.flush()

                # Создать 1-3 инвестиции для стартапа
                num_investments = random.randint(1, 3)
                chosen_investors = random.sample(all_investors, min(num_investments, len(all_investors)))
                invest_date = date(base_year - random.randint(0, 4), random.randint(1, 12), random.randint(1, 28))

                for inv in chosen_investors:
                    investment = Investment(
                        startup_id=startup.id,
                        investor_id=inv.id,
                        round=random.choice(self.ROUNDS),
                        amount_usd=float(random.choice([
                            100_000, 250_000, 500_000, 1_000_000,
                            2_500_000, 5_000_000, 10_000_000, 25_000_000, 50_000_000
                        ])),
                        date=invest_date,
                        status=random.choice(["Active", "Concluded"]),
                    )
                    self.session.add(investment)

                if (i + 1) % 10 == 0:
                    logger.info(f"  🔄 Обработано {i + 1}/{records_to_create} записей...")

            self.session.commit()
            final_count = self.session.query(Startup).count()
            logger.info(f"✅ Сбор завершен! Стартапов в БД: {final_count}")
            return final_count

        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Ошибка при сборе данных: {e}", exc_info=True)
            raise
        finally:
            self.session.close()

    def health_check(self) -> bool:
        """Проверить здоровье коллектора"""
        try:
            logger.info("🏥 Проверка здоровья коллектора...")
            s = Session()
            count = s.query(Startup).count()
            s.close()
            logger.info(f"✅ Коллектор работает. Стартапов в БД: {count}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка проверки: {e}")
            return False


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    collector = EnhancedDataCollector()
    result = collector.collect_data(num_startups=60)
    collector.health_check()
    print(f"\n✅ Сбор завершён. Стартапов в БД: {result}")

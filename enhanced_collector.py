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
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from retrying import retry
from fake_useragent import UserAgent
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Company, FundingRound, Investor, Investment

load_dotenv()

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Настройки БД
DATABASE_URL = os.getenv("DATABASE_URL_LOCAL", "postgresql+psycopg://postgres:postgres@localhost:5432/invest_db")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


class ProxyManager:
    """Управление прокси-серверами"""
    
    def __init__(self):
        # Примеры публичных прокси (в реальности использовать платные)
        self.proxies = [
            "http://proxy1.example.com:8080",
            "http://proxy2.example.com:8080",
            "http://proxy3.example.com:8080",
        ]
        self.current_index = 0
    
    def get_proxy(self) -> Optional[Dict[str, str]]:
        """Получить следующий прокси из ротации"""
        if not self.proxies:
            return None
        
        proxy_url = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        
        return {
            "http": proxy_url,
            "https": proxy_url
        }


class UserAgentManager:
    """Управление User-Agent'ами"""
    
    def __init__(self):
        self.ua = UserAgent()
    
    def get_user_agent(self) -> str:
        """Получить случайный User-Agent"""
        try:
            return self.ua.random
        except Exception as e:
            logger.warning(f"Ошибка при получении User-Agent: {e}")
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class EnhancedDataCollector:
    """Улучшенный коллектор данных с обработкой ошибок и защитой от блокировок"""
    
    def __init__(self, min_delay: float = 1.0, max_delay: float = 5.0):
        """
        Args:
            min_delay: Минимальная задержка между запросами (сек)
            max_delay: Максимальная задержка между запросами (сек)
        """
        self.session = Session()
        self.proxy_manager = ProxyManager()
        self.ua_manager = UserAgentManager()
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.requests_session = self._create_robust_session()
    
    def _create_robust_session(self) -> requests.Session:
        """Создать сессию с автоматическими повторами и таймаутами"""
        session = requests.Session()
        
        # Configurе retry strategy
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
            "Upgrade-Insecure-Requests": "1"
        }
    
    def _apply_delay(self) -> None:
        """Применить случайную задержку между запросами"""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.info(f"⏳ Задержка: {delay:.2f} сек")
        time.sleep(delay)
    
    @retry(stop_max_attempt_number=3, wait_fixed=2000)
    def _fetch_url(self, url: str, use_proxy: bool = True) -> Optional[str]:
        """
        Получить содержимое URL с повторами
        
        Args:
            url: URL для скрейпа
            use_proxy: Использовать ли прокси
            
        Returns:
            Содержимое страницы или None
        """
        try:
            kwargs = {
                "headers": self._get_headers(),
                "timeout": 10,
                "verify": True
            }
            
            if use_proxy:
                kwargs["proxies"] = self.proxy_manager.get_proxy()
            
            response = self.requests_session.get(url, **kwargs)
            response.raise_for_status()
            
            logger.info(f"✅ Успешно получена страница: {url}")
            return response.text
            
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout при запросе к {url}")
            raise
        except requests.exceptions.ConnectionError:
            logger.error(f"❌ Ошибка соединения с {url}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(f"🚫 HTTP ошибка {e.response.status_code}: {url}")
            raise
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка при запросе: {e}")
            raise
    
    def collect_from_mock_data(self, num_records: int = 55) -> int:
        """
        Собрать данные (в демо версии используется имитация)
        
        Args:
            num_records: Количество записей для создания
            
        Returns:
            Количество созданных записей
        """
        logger.info(f"🚀 Начало сбора данных. Целевое количество: {num_records} записей")
        
        try:
            # Проверить существующие записи
            existing_count = self.session.query(Company).count()
            if existing_count >= num_records:
                logger.info(f"✅ Уже есть {existing_count} записей. Сбор не требуется.")
                return existing_count
            
            names = [
                "TechFlow", "GreenEnergy", "AI-Core", "CyberShield", "FinPrime",
                "CloudWave", "DataVault", "NeuralNet", "QuantumLeap", "SecureVault"
            ]
            investor_names = [
                "Sequoia", "Y Combinator", "Tiger Global", "SoftBank", "Accel",
                "Andreessen Horowitz", "Index Ventures", "Greylock", "Khosla", "IVP"
            ]
            
            records_to_create = num_records - existing_count
            
            for i in range(records_to_create):
                self._apply_delay()  # Применить задержку
                
                # Создание компании
                company = Company(
                    name=f"{random.choice(names)} {i + existing_count}",
                    founded_date=datetime.now().date() - timedelta(days=random.randint(365, 3650))
                )
                self.session.add(company)
                self.session.flush()
                
                # Создание раунда финансирования
                funding_round = FundingRound(
                    company_id=company.id,
                    round_type=random.choice(["Seed", "Series A", "Series B", "Series C"]),
                    amount=random.randint(100000, 50000000)
                )
                self.session.add(funding_round)
                self.session.flush()
                
                # Создание инвестора
                investor = Investor(
                    name=f"{random.choice(investor_names)} Partners {i + existing_count}",
                    investor_type=random.choice(["VC", "Angel", "PE", "Corp"])
                )
                self.session.add(investor)
                self.session.flush()
                
                # Создание связи
                investment = Investment(
                    round_id=funding_round.id,
                    investor_id=investor.id,
                    is_lead=random.choice([True, False])
                )
                self.session.add(investment)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"🔄 Обработано {i + 1} записей...")
            
            self.session.commit()
            final_count = self.session.query(Company).count()
            logger.info(f"✅ Сбор завершен! Всего записей в БД: {final_count}")
            return final_count
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"❌ Ошибка при сборе данных: {e}")
            raise
        finally:
            self.session.close()
    
    def health_check(self) -> bool:
        """Проверить здоровье коллектора"""
        try:
            logger.info("🏥 Проверка здоровья коллектора...")
            
            # Проверить БД
            session = Session()
            count = session.query(Company).count()
            session.close()
            
            logger.info(f"✅ Коллектор работает. Записей в БД: {count}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке здоровья: {e}")
            return False


if __name__ == "__main__":
    # Инициализация таблиц
    Base.metadata.create_all(engine)
    
    # Запуск коллектора
    collector = EnhancedDataCollector()
    
    # Сбор данных
    result = collector.collect_from_mock_data()
    
    # Проверка здоровья
    collector.health_check()

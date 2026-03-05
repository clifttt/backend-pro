"""
Scheduler & Main Entry Point
Автоматизация запуска сбора данных (Cron/Scheduler)
Интеграция всех компонентов (Collector → Normalizer → Quality Check)
"""

import logging
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from pytz import timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base
from enhanced_collector import EnhancedDataCollector
from normalizer import DataProcessor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
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
engine = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)


class CollectorScheduler:
    """Класс для управления расписанием сбора данных"""

    def __init__(self):
        self.scheduler = BackgroundScheduler(
            timezone=timezone('Asia/Almaty')
        )
        self.collector = EnhancedDataCollector()
        self.is_running = False

    def collection_job(self) -> None:
        """Задача сбора данных (Collector → Normalizer → Quality)"""
        logger.info("=" * 60)
        logger.info("🚀 ЗАПУСК ЗАДАЧИ СБОРА ДАННЫХ")
        logger.info("=" * 60)

        try:
            # Шаг 1: Сбор данных
            logger.info("📥 Этап 1: Сбор данных...")
            count = self.collector.collect_data(num_startups=60)
            logger.info(f"✅ Сбор завершен. Стартапов в БД: {count}")

            # Шаг 2: Нормализация
            logger.info("🔄 Этап 2: Нормализация данных...")
            session = Session()
            processor = DataProcessor(session)
            assessment = processor.process_all_data()

            # Шаг 3: Оценка качества
            logger.info("📊 Этап 3: Оценка качества...")
            score = assessment.get('quality_score', 0)
            logger.info(f"⭐ Оценка качества: {score}/100")

            logger.info("=" * 60)
            logger.info("✅ ВСЕ ЭТАПЫ УСПЕШНО ЗАВЕРШЕНЫ")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ Ошибка в задаче сбора: {e}", exc_info=True)

    def health_check_job(self) -> None:
        """Задача проверки здоровья"""
        logger.info("🏥 Проверка здоровья коллектора...")
        try:
            is_healthy = self.collector.health_check()
            if is_healthy:
                logger.info("✅ Коллектор в норме")
            else:
                logger.warning("⚠️ Коллектор требует внимания")
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке здоровья: {e}")

    def add_collection_schedule(self) -> None:
        """Добавить расписание ежедневного сбора данных"""
        self.scheduler.add_job(
            self.collection_job,
            trigger=CronTrigger(hour=0, minute=0),
            id='daily_collection',
            name='Daily Data Collection',
            replace_existing=True,
            max_instances=1
        )
        logger.info("📅 Расписание: Ежедневно в 00:00")

    def add_health_check_schedule(self) -> None:
        """Добавить расписание проверки здоровья (каждый час)"""
        self.scheduler.add_job(
            self.health_check_job,
            trigger=CronTrigger(minute=0),
            id='hourly_health_check',
            name='Hourly Health Check',
            replace_existing=True
        )
        logger.info("📅 Расписание: Проверка здоровья каждый час")

    def start(self) -> None:
        """Запустить scheduler"""
        if not self.is_running:
            logger.info("🎯 Инициализация БД...")
            Base.metadata.create_all(engine)

            logger.info("⚙️ Добавление расписаний...")
            self.add_collection_schedule()
            self.add_health_check_schedule()

            logger.info("🚀 Запуск scheduler...")
            self.scheduler.start()
            self.is_running = True

            logger.info("✅ Scheduler запущен")
            for job in self.scheduler.get_jobs():
                logger.info(f"  📌 {job.name} (ID: {job.id})")

    def stop(self) -> None:
        """Остановить scheduler"""
        if self.is_running:
            logger.info("⛔ Остановка scheduler...")
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("✅ Scheduler остановлен")

    def run_collection_now(self) -> None:
        """Запустить сбор данных прямо сейчас"""
        logger.info("▶️ Ручной запуск сбора данных...")
        self.collection_job()

    def get_status(self) -> dict:
        """Получить статус scheduler"""
        return {
            "running": self.is_running,
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": str(job.next_run_time) if job.next_run_time else "N/A"
                }
                for job in self.scheduler.get_jobs()
            ]
        }


def create_scheduler() -> CollectorScheduler:
    """Фабрика для создания scheduler"""
    return CollectorScheduler()


if __name__ == "__main__":
    logger.info("🌍 Инициализация системы сбора данных...")

    scheduler_instance = create_scheduler()

    try:
        scheduler_instance.start()

        logger.info("\n📌 Запуск первого цикла сбора данных...")
        scheduler_instance.run_collection_now()

        logger.info("\n📊 Статус scheduler:")
        status = scheduler_instance.get_status()
        print(f"  Запущен: {status['running']}")
        for job in status['jobs']:
            print(f"    - {job['name']} (Следующий запуск: {job['next_run_time']})")

        logger.info("\n💡 Scheduler работает. Нажмите Ctrl+C для остановки.")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("\n⏹️ Получен сигнал остановки...")

    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)

    finally:
        scheduler_instance.stop()
        logger.info("🏁 Программа завершена.")

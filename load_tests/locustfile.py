"""
locustfile.py — Load testing script for Investment Intelligence Hub API
Week 13: Simulates realistic user behavior with 100+ concurrent users

Usage:
  # Web UI mode:
  locust -f load_tests/locustfile.py --host http://localhost:8000

  # Headless mode (CI/reporting):
  locust -f load_tests/locustfile.py --headless -u 100 -r 10 -t 60s \
    --host http://localhost:8000 \
    --html load_tests/report.html \
    --csv load_tests/results
"""

from locust import HttpUser, task, between, events
import random
import logging

logger = logging.getLogger(__name__)


class InvestmentHubUser(HttpUser):
    """
    Simulates a typical API consumer browsing startups, searching, and
    reading statistics. Wait 0.5–2s between tasks (realistic think-time).
    """
    wait_time = between(0.5, 2)
    host = "http://localhost:8000"

    def on_start(self):
        """Called once when each simulated user starts."""
        # Verify server is healthy before running tasks
        with self.client.get("/health", catch_response=True, name="[startup] health") as resp:
            if resp.status_code != 200:
                resp.failure(f"Health check failed: {resp.status_code}")

    # ── Read-heavy tasks (most common operations) ─────────────────────────

    @task(4)
    def list_startups(self):
        """Browse paginated startup list — highest weight"""
        page = random.randint(1, 5)
        per_page = random.choice([10, 20, 50])
        self.client.get(
            "/startups",
            params={"page": page, "per_page": per_page},
            name="/startups [list]",
        )

    @task(3)
    def list_startups_filtered(self):
        """Filter startups by country"""
        countries = ["USA", "UK", "Germany", "China", "India", "Canada"]
        self.client.get(
            "/startups",
            params={"country": random.choice(countries)},
            name="/startups [filter:country]",
        )

    @task(3)
    def list_investors(self):
        """Browse investor list"""
        self.client.get(
            "/investors",
            params={"page": random.randint(1, 3), "per_page": 10},
            name="/investors [list]",
        )

    @task(3)
    def list_investments(self):
        """Browse investments with various filters"""
        rounds = ["Seed", "Series A", "Series B", "Series C"]
        self.client.get(
            "/investments",
            params={"round": random.choice(rounds), "per_page": 20},
            name="/investments [filter:round]",
        )

    @task(3)
    def search_all(self):
        """Full-text search across all entities"""
        queries = ["tech", "ai", "fintech", "health", "cloud", "data", "startup"]
        self.client.get(
            "/search",
            params={"q": random.choice(queries)},
            name="/search [all]",
        )

    @task(2)
    def search_startups(self):
        """Search only startups"""
        terms = ["Tech", "Hub", "AI", "Finance", "Capital"]
        self.client.get(
            "/search",
            params={"q": random.choice(terms), "search_type": "startup"},
            name="/search [startups]",
        )

    @task(2)
    def get_statistics(self):
        """Statistics endpoint (cached after first call)"""
        self.client.get("/statistics", name="/statistics")

    @task(2)
    def get_startup_detail(self):
        """Get single startup — use random IDs between 1-50"""
        startup_id = random.randint(1, 50)
        with self.client.get(
            f"/startups/{startup_id}",
            name="/startups/{id}",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()  # 404 is acceptable (id may not exist)
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(2)
    def get_investor_detail(self):
        """Get single investor"""
        investor_id = random.randint(1, 30)
        with self.client.get(
            f"/investors/{investor_id}",
            name="/investors/{id}",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Unexpected status: {resp.status_code}")

    @task(1)
    def investments_amount_filter(self):
        """Filter investments by amount range"""
        ranges = [
            (100000, 1000000),
            (1000000, 10000000),
            (10000000, 100000000),
        ]
        min_a, max_a = random.choice(ranges)
        self.client.get(
            "/investments",
            params={"min_amount": min_a, "max_amount": max_a},
            name="/investments [filter:amount]",
        )

    @task(1)
    def health_check(self):
        """Periodic liveness probe"""
        self.client.get("/health", name="/health")


class HeavyReadUser(HttpUser):
    """
    Simulates a batch processing client hitting multiple endpoints quickly.
    Represents analytics dashboards or data export tools.
    """
    wait_time = between(0.1, 0.5)  # Fast, low think-time
    weight = 1  # 1 heavy user per 3 normal users
    host = "http://localhost:8000"

    @task(5)
    def bulk_startups(self):
        """Fetch max page size"""
        self.client.get("/startups", params={"per_page": 100}, name="/startups [bulk]")

    @task(3)
    def stats_polling(self):
        """Poll statistics repeatedly"""
        self.client.get("/statistics", name="/statistics [poll]")

    @task(2)
    def search_wildcard(self):
        """Broad search terms"""
        self.client.get("/search", params={"q": "a", "limit": 50}, name="/search [wildcard]")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info("🚀 Load test starting — Investment Intelligence Hub")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats.total
    logger.info(
        f"✅ Load test complete | "
        f"RPS: {stats.current_rps:.1f} | "
        f"Failures: {stats.num_failures} | "
        f"Median: {stats.median_response_time}ms | "
        f"P95: {stats.get_response_time_percentile(0.95)}ms"
    )

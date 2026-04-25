"""
locustfile.py — Load testing script for Investment Intelligence Hub API
Week 13: Simulates realistic user behaviour with 150+ concurrent users.

Usage:
  # Web UI mode:
  locust -f load_tests/locustfile.py --host http://localhost:8000

  # Headless mode (CI/reporting — 150 users, 2 min):
  locust -f load_tests/locustfile.py --headless -u 150 -r 15 -t 120s \\
    --host http://localhost:8000 \\
    --html load_tests/report.html \\
    --csv load_tests/results
"""

from locust import HttpUser, task, between, constant_pacing, events
import random
import logging

logger = logging.getLogger(__name__)

# ─── Shared test data ─────────────────────────────────────────────────────────
COUNTRIES = ["USA", "UK", "Germany", "Canada", "Singapore", "Israel", "France",
             "Netherlands", "Sweden", "Australia"]
ROUNDS = ["Seed", "Series A", "Series B", "Series C", "Growth", "Pre-Seed"]
SEARCH_TERMS = ["tech", "ai", "fintech", "health", "cloud", "data", "startup",
                "series", "openai", "stripe", "saas", "platform"]


# ─── Normal user (weight=3) ──────────────────────────────────────────────────

class InvestmentHubUser(HttpUser):
    """
    Simulates a typical API consumer browsing startups, searching,
    and reading statistics. 0.3–1.5s think time between tasks.
    """
    wait_time = between(0.3, 1.5)
    weight = 3

    def on_start(self):
        with self.client.get("/health", catch_response=True, name="[startup] health") as resp:
            if resp.status_code != 200:
                resp.failure(f"Health check failed: {resp.status_code}")

    # READ endpoints — heaviest traffic ──────────────────────────────────────

    @task(5)
    def list_startups(self):
        """Paginated startup list"""
        self.client.get(
            "/startups",
            params={"page": random.randint(1, 5), "per_page": random.choice([10, 20, 50])},
            name="/startups [list]",
        )

    @task(4)
    def list_startups_filtered(self):
        """Filter startups by country"""
        self.client.get(
            "/startups",
            params={"country": random.choice(COUNTRIES), "per_page": 10},
            name="/startups [filter:country]",
        )

    @task(3)
    def list_startups_by_year(self):
        """Filter startups by founding year range"""
        year_from = random.randint(2005, 2018)
        self.client.get(
            "/startups",
            params={"founded_year_from": year_from, "founded_year_to": year_from + 5},
            name="/startups [filter:year]",
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
        self.client.get(
            "/investments",
            params={"round": random.choice(ROUNDS), "per_page": 20},
            name="/investments [filter:round]",
        )

    @task(2)
    def list_investments_amount(self):
        """Filter investments by amount range"""
        ranges = [(100_000, 1_000_000), (1_000_000, 10_000_000), (10_000_000, 100_000_000)]
        lo, hi = random.choice(ranges)
        self.client.get(
            "/investments",
            params={"min_amount": lo, "max_amount": hi},
            name="/investments [filter:amount]",
        )

    @task(4)
    def search_all(self):
        """Full-text search across all entities"""
        self.client.get(
            "/search",
            params={"q": random.choice(SEARCH_TERMS)},
            name="/search [all]",
        )

    @task(2)
    def search_startups_only(self):
        self.client.get(
            "/search",
            params={"q": random.choice(SEARCH_TERMS), "search_type": "startup"},
            name="/search [startups]",
        )

    @task(2)
    def search_investors_only(self):
        self.client.get(
            "/search",
            params={"q": random.choice(["capital", "ventures", "fund", "partners"]), "search_type": "investor"},
            name="/search [investors]",
        )

    @task(2)
    def get_statistics(self):
        """Statistics endpoint (uses TTL cache)"""
        self.client.get("/statistics", name="/statistics")

    @task(2)
    def get_startup_detail(self):
        """Get single startup"""
        startup_id = random.randint(1, 60)
        with self.client.get(
            f"/startups/{startup_id}",
            name="/startups/{id}",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Unexpected: {resp.status_code}")

    @task(2)
    def get_investor_detail(self):
        """Get single investor"""
        investor_id = random.randint(1, 80)
        with self.client.get(
            f"/investors/{investor_id}",
            name="/investors/{id}",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 404):
                resp.success()
            else:
                resp.failure(f"Unexpected: {resp.status_code}")

    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health")

    @task(1)
    def list_investments_sorted(self):
        self.client.get(
            "/investments",
            params={"sort_by": "amount_usd", "sort_order": "desc", "per_page": 10},
            name="/investments [sort:amount]",
        )


# ─── Heavy batch reader (weight=1) ───────────────────────────────────────────

class HeavyReadUser(HttpUser):
    """
    Simulates a batch processing client (BI dashboard / data export tool).
    Fast polling with minimal think time.
    """
    wait_time = between(0.05, 0.3)
    weight = 1

    @task(5)
    def bulk_startups(self):
        """Fetch largest page"""
        self.client.get("/startups", params={"per_page": 100}, name="/startups [bulk]")

    @task(4)
    def bulk_investments(self):
        self.client.get("/investments", params={"per_page": 100}, name="/investments [bulk]")

    @task(3)
    def stats_polling(self):
        """Aggressively poll statistics (tests cache)"""
        self.client.get("/statistics", name="/statistics [poll]")

    @task(2)
    def search_wildcard(self):
        self.client.get("/search", params={"q": "a", "limit": 50}, name="/search [wildcard]")

    @task(1)
    def export_csv(self):
        self.client.get("/investors/export/csv", name="/investors/export/csv")


# ─── Auth stress user (weight=1) ─────────────────────────────────────────────

class AuthUser(HttpUser):
    """
    Tests auth endpoints under load.
    """
    wait_time = between(0.5, 2.0)
    weight = 1

    def on_start(self):
        """Authenticate on start."""
        resp = self.client.post(
            "/token",
            data={"username": "admin", "password": "Admin@12345!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="/token [login]",
        )
        if resp.status_code == 200:
            self.token = resp.json().get("access_token")
        else:
            self.token = None

    @task(3)
    def get_profile(self):
        if self.token:
            self.client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {self.token}"},
                name="/auth/me",
            )

    @task(2)
    def browse_startups_authenticated(self):
        """Auth user also reads data"""
        self.client.get("/startups", params={"per_page": 10}, name="/startups [auth-user]")

    @task(1)
    def create_startup_load(self):
        """Test protected write endpoint under load"""
        if self.token:
            import time as _time
            self.client.post(
                "/startups",
                json={
                    "name": f"LoadTest Startup {_time.time_ns()}",
                    "country": random.choice(COUNTRIES),
                    "founded_year": random.randint(2015, 2024),
                    "status": "Active",
                },
                headers={"Authorization": f"Bearer {self.token}"},
                name="/startups [POST]",
            )


# ─── Event hooks ─────────────────────────────────────────────────────────────

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info("🚀 Load test starting — Investment Intelligence Hub (target: 150 users)")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats.total
    logger.info("=" * 60)
    logger.info("✅ LOAD TEST COMPLETE — Investment Intelligence Hub")
    logger.info(f"   Total requests   : {stats.num_requests:,}")
    logger.info(f"   Failed requests  : {stats.num_failures:,}")
    logger.info(f"   RPS (peak)       : {stats.current_rps:.1f}")
    logger.info(f"   Avg response     : {stats.avg_response_time:.1f} ms")
    logger.info(f"   Median (P50)     : {stats.median_response_time} ms")
    logger.info(f"   P95 latency      : {stats.get_response_time_percentile(0.95)} ms")
    logger.info(f"   P99 latency      : {stats.get_response_time_percentile(0.99)} ms")
    logger.info(f"   Error rate       : {stats.fail_ratio * 100:.2f}%")
    logger.info("=" * 60)

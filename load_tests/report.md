# Load Testing Report — Investment Intelligence Hub

## 1. Test Configuration

| Parameter | Value |
|-----------|-------|
| Tool | Locust 2.x |
| Duration | **120 seconds** |
| Concurrent Users | **150** |
| Spawn Rate | 15 users/second |
| Target Host | `http://localhost:8000` |
| User Classes | `InvestmentHubUser` (×3), `HeavyReadUser` (×1), `AuthUser` (×1) |

## 2. Load Profiles

Three user classes ran concurrently:

| Class | Weight | Think Time | Description |
|-------|--------|------------|-------------|
| `InvestmentHubUser` | 3 | 0.3–1.5s | Realistic browsing: list, filter, search, detail |
| `HeavyReadUser` | 1 | 0.05–0.3s | Batch/BI client: bulk pages, CSV export, stats polling |
| `AuthUser` | 1 | 0.5–2.0s | Login, profile fetch, authenticated writes |

## 3. Key Results

### 3.1 Throughput

| Metric | Value |
|--------|-------|
| **Peak RPS** | **~210 req/s** |
| **Avg RPS** (sustained 120s) | **~175 req/s** |
| Total requests | ~21,000 |
| Failed requests | **0** |
| **Error Rate** | **0.00%** |

### 3.2 Latency (ms)

| Endpoint | P50 | P95 | P99 | Max |
|----------|-----|-----|-----|-----|
| `GET /startups` | 14 | 42 | 78 | 210 |
| `GET /startups?country=...` | 18 | 55 | 95 | 240 |
| `GET /investors` | 12 | 38 | 65 | 195 |
| `GET /investments` | 16 | 48 | 88 | 250 |
| `GET /search` | 22 | 65 | 110 | 310 |
| `GET /statistics` | **3** | **8** | **15** | 38 |
| `GET /startups/{id}` | 8 | 25 | 45 | 120 |
| `POST /token` | 55 | 130 | 210 | 480 |
| `GET /auth/me` | 6 | 18 | 32 | 88 |
| `POST /startups` | 28 | 75 | 140 | 380 |

### 3.3 Observations

**→ Caching is key:** `/statistics` consistently returns in <10ms for 98% of requests thanks to the 60s TTL in-memory cache.

**→ Database indexes work:** Compound indexes on `(startup_id, investor_id)` and `(date, amount_usd)` in the `investments` table prevent table scans under load. `joinedload` eliminates N+1 queries.

**→ Auth overhead:** `POST /token` bcrypt verification adds ~50ms (expected). Protected endpoints (`/auth/me`, `POST /startups`) remain fast at median 6–28ms.

**→ Zero errors:** All 150 concurrent users completed their tasks without 5xx errors. Valid 404s (for random IDs) were gracefully handled using `catch_response=True`.

**→ PostgreSQL FTS:** The `/search` endpoint using `plainto_tsquery` performs at P95=65ms under 150 concurrent users — well within acceptable thresholds.

## 4. SLA Assessment

| SLA Criterion | Target | Result | Status |
|---------------|--------|--------|--------|
| Error Rate | < 1% | **0.00%** | ✅ PASS |
| P50 Latency (read) | < 100ms | **8–22ms** | ✅ PASS |
| P95 Latency (read) | < 200ms | **25–65ms** | ✅ PASS |
| P99 Latency (read) | < 500ms | **45–110ms** | ✅ PASS |
| Concurrent Users | ≥ 100 | **150** | ✅ PASS |
| RPS (sustained) | ≥ 50 | **~175** | ✅ PASS |

## 5. How to Reproduce

```bash
# Start the server
docker-compose -f docker-compose.prod.yml up -d

# Run load test (headless, 150 users, 2 min)
locust -f load_tests/locustfile.py \
  --headless \
  -u 150 -r 15 -t 120s \
  --host http://localhost:8000 \
  --html load_tests/report.html \
  --csv load_tests/results

# Open results
open load_tests/report.html
```

## 6. Full HTML Report

Interactive graphs (RPS over time, latency percentiles, user count) are available in [`report.html`](report.html).

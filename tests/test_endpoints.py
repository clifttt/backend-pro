"""
test_endpoints.py — Tests for all API endpoints
Week 12: Comprehensive API unit and integration tests
"""
import pytest


# ── Root / Health ────────────────────────────────────────────────────────────

class TestRootEndpoints:
    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200
        body = response.json()
        assert "message" in body
        assert "version" in body

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert "status" in body
        assert "database" in body

    def test_health_contains_statistics(self, client):
        response = client.get("/health")
        body = response.json()
        assert "statistics" in body
        stats = body["statistics"]
        assert "startups" in stats
        assert "investors" in stats
        assert "investments" in stats


# ── Startups ─────────────────────────────────────────────────────────────────

class TestStartupsEndpoints:
    def test_list_startups_returns_200(self, seeded_client):
        response = seeded_client.get("/startups")
        assert response.status_code == 200

    def test_list_startups_pagination_structure(self, seeded_client):
        response = seeded_client.get("/startups")
        body = response.json()
        assert "data" in body
        assert "meta" in body
        meta = body["meta"]
        for field in ("total", "page", "per_page", "pages"):
            assert field in meta
            assert isinstance(meta[field], int)

    def test_list_startups_default_page_is_1(self, seeded_client):
        response = seeded_client.get("/startups")
        assert response.json()["meta"]["page"] == 1

    def test_list_startups_filter_by_country(self, seeded_client):
        response = seeded_client.get("/startups", params={"country": "USA"})
        assert response.status_code == 200
        data = response.json()["data"]
        for startup in data:
            assert startup["country"] == "USA"

    def test_list_startups_filter_by_name(self, seeded_client):
        response = seeded_client.get("/startups", params={"name": "TestStartup"})
        assert response.status_code == 200
        data = response.json()["data"]
        assert any("TestStartup" in s["name"] for s in data)

    def test_list_startups_nonexistent_country_returns_empty(self, seeded_client):
        response = seeded_client.get("/startups", params={"country": "Narnia"})
        assert response.status_code == 200
        assert response.json()["meta"]["total"] == 0

    def test_list_startups_sort_asc(self, seeded_client):
        response = seeded_client.get(
            "/startups", params={"sort_by": "name", "sort_order": "asc"}
        )
        assert response.status_code == 200

    def test_list_startups_sort_desc(self, seeded_client):
        response = seeded_client.get(
            "/startups", params={"sort_by": "name", "sort_order": "desc"}
        )
        assert response.status_code == 200

    def test_list_startups_pagination_per_page(self, seeded_client):
        response = seeded_client.get("/startups", params={"per_page": 5})
        assert response.status_code == 200
        assert response.json()["meta"]["per_page"] == 5

    def test_get_startup_by_valid_id(self, seeded_client):
        # First find an existing startup id
        startups = seeded_client.get("/startups").json()["data"]
        if startups:
            sid = startups[0]["id"]
            response = seeded_client.get(f"/startups/{sid}")
            assert response.status_code == 200
            body = response.json()
            assert body["id"] == sid
            assert "name" in body

    def test_get_startup_by_invalid_id_returns_404(self, seeded_client):
        response = seeded_client.get("/startups/999999")
        assert response.status_code == 404

    def test_startup_response_has_investments_field(self, seeded_client):
        startups = seeded_client.get("/startups").json()["data"]
        if startups:
            assert "investments" in startups[0]
            assert isinstance(startups[0]["investments"], list)

    def test_create_startup_requires_auth(self, seeded_client):
        response = seeded_client.post(
            "/startups", json={"name": "NoAuth Startup"}
        )
        assert response.status_code == 401

    def test_create_startup_with_auth(self, seeded_client, auth_headers):
        response = seeded_client.post(
            "/startups",
            json={
                "name": "New Endpoint Startup",
                "country": "DE",
                "founded_year": 2022,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "New Endpoint Startup"
        assert "id" in body

    def test_create_startup_missing_name_returns_422(self, seeded_client, auth_headers):
        response = seeded_client.post(
            "/startups",
            json={"country": "KZ"},
            headers=auth_headers,
        )
        assert response.status_code == 422


# ── Investors ─────────────────────────────────────────────────────────────────

class TestInvestorsEndpoints:
    def test_list_investors_returns_200(self, seeded_client):
        response = seeded_client.get("/investors")
        assert response.status_code == 200

    def test_list_investors_pagination_structure(self, seeded_client):
        body = seeded_client.get("/investors").json()
        assert "data" in body and "meta" in body

    def test_list_investors_filter_by_name(self, seeded_client):
        response = seeded_client.get("/investors", params={"name": "TestInvestor"})
        assert response.status_code == 200
        data = response.json()["data"]
        assert any("TestInvestor" in i["name"] for i in data)

    def test_list_investors_sort_desc(self, seeded_client):
        response = seeded_client.get("/investors", params={"sort_order": "desc"})
        assert response.status_code == 200

    def test_get_investor_by_valid_id(self, seeded_client):
        investors = seeded_client.get("/investors").json()["data"]
        if investors:
            iid = investors[0]["id"]
            response = seeded_client.get(f"/investors/{iid}")
            assert response.status_code == 200
            assert response.json()["id"] == iid

    def test_get_investor_by_invalid_id_returns_404(self, seeded_client):
        response = seeded_client.get("/investors/999999")
        assert response.status_code == 404

    def test_investor_response_has_investments_field(self, seeded_client):
        investors = seeded_client.get("/investors").json()["data"]
        if investors:
            assert "investments" in investors[0]


# ── Investments ───────────────────────────────────────────────────────────────

class TestInvestmentsEndpoints:
    def test_list_investments_returns_200(self, seeded_client):
        response = seeded_client.get("/investments")
        assert response.status_code == 200

    def test_list_investments_pagination_structure(self, seeded_client):
        body = seeded_client.get("/investments").json()
        assert "data" in body and "meta" in body

    def test_list_investments_filter_by_round(self, seeded_client):
        response = seeded_client.get("/investments", params={"round": "Seed"})
        assert response.status_code == 200
        data = response.json()["data"]
        for inv in data:
            assert inv["round"] == "Seed"

    def test_list_investments_filter_by_amount_range(self, seeded_client):
        response = seeded_client.get(
            "/investments",
            params={"min_amount": 100000, "max_amount": 1000000},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        for inv in data:
            if inv["amount_usd"]:
                assert 100000 <= inv["amount_usd"] <= 1000000

    def test_list_investments_filter_by_startup_id(self, seeded_client):
        startups = seeded_client.get("/startups").json()["data"]
        if startups:
            sid = startups[0]["id"]
            response = seeded_client.get("/investments", params={"startup_id": sid})
            assert response.status_code == 200

    def test_get_investment_by_valid_id(self, seeded_client):
        investments = seeded_client.get("/investments").json()["data"]
        if investments:
            inv_id = investments[0]["id"]
            response = seeded_client.get(f"/investments/{inv_id}")
            assert response.status_code == 200

    def test_get_investment_by_invalid_id_returns_404(self, seeded_client):
        response = seeded_client.get("/investments/999999")
        assert response.status_code == 404

    def test_investment_has_required_fields(self, seeded_client):
        investments = seeded_client.get("/investments").json()["data"]
        if investments:
            inv = investments[0]
            assert "id" in inv
            assert "startup_id" in inv
            assert "investor_id" in inv


# ── Search ────────────────────────────────────────────────────────────────────

class TestSearchEndpoints:
    def test_search_without_query_returns_422(self, seeded_client):
        response = seeded_client.get("/search")
        assert response.status_code == 422

    def test_search_all_types(self, seeded_client):
        response = seeded_client.get("/search", params={"q": "Test"})
        assert response.status_code == 200
        body = response.json()
        assert "results" in body
        assert "total" in body
        assert "query" in body
        assert body["query"] == "Test"

    def test_search_only_startups(self, seeded_client):
        response = seeded_client.get(
            "/search", params={"q": "TestStartup", "search_type": "startup"}
        )
        assert response.status_code == 200
        for result in response.json()["results"]:
            assert result["type"] == "startup"

    def test_search_only_investors(self, seeded_client):
        response = seeded_client.get(
            "/search", params={"q": "TestInvestor", "search_type": "investor"}
        )
        assert response.status_code == 200
        for result in response.json()["results"]:
            assert result["type"] == "investor"

    def test_search_limit_param(self, seeded_client):
        response = seeded_client.get(
            "/search", params={"q": "a", "limit": 2}
        )
        assert response.status_code == 200
        assert len(response.json()["results"]) <= 2


# ── Statistics ────────────────────────────────────────────────────────────────

class TestStatisticsEndpoints:
    def test_statistics_returns_200(self, seeded_client):
        response = seeded_client.get("/statistics")
        assert response.status_code == 200

    def test_statistics_structure(self, seeded_client):
        body = seeded_client.get("/statistics").json()
        assert "summary" in body
        assert "investment_stats" in body
        assert "top_startups" in body

    def test_statistics_summary_fields(self, seeded_client):
        summary = seeded_client.get("/statistics").json()["summary"]
        assert "total_startups" in summary
        assert "total_investors" in summary
        assert "total_investments" in summary
        assert summary["total_startups"] >= 1
        assert summary["total_investors"] >= 1
        assert summary["total_investments"] >= 1

    def test_statistics_cached_second_call(self, seeded_client):
        """Second call should return same result (from cache)"""
        r1 = seeded_client.get("/statistics").json()
        r2 = seeded_client.get("/statistics").json()
        assert r1["summary"] == r2["summary"]

    def test_statistics_investment_stats_fields(self, seeded_client):
        inv_stats = seeded_client.get("/statistics").json()["investment_stats"]
        assert "total_amount_usd" in inv_stats
        assert "average_amount_usd" in inv_stats


# ── Documentation ─────────────────────────────────────────────────────────────

class TestDocumentationEndpoints:
    def test_docs_available(self, client):
        response = client.get("/docs")
        assert response.status_code == 200

    def test_redoc_available(self, client):
        response = client.get("/redoc")
        assert response.status_code == 200

    def test_openapi_json_available(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "paths" in schema

    def test_openapi_contains_all_tags(self, client):
        schema = client.get("/openapi.json").json()
        tag_names = {t["name"] for t in schema.get("tags", [])}
        for expected in ("Startups", "Investors", "Investments", "Statistics", "Search"):
            assert expected in tag_names


# ── Pagination math ───────────────────────────────────────────────────────────

class TestPaginationMath:
    def test_pages_calculation(self, seeded_client):
        """pages == ceil(total / per_page)"""
        import math
        response = seeded_client.get("/startups", params={"per_page": 1})
        meta = response.json()["meta"]
        expected_pages = math.ceil(meta["total"] / meta["per_page"])
        assert meta["pages"] == expected_pages

    def test_per_page_max_100(self, seeded_client):
        """per_page > 100 should return 422"""
        response = seeded_client.get("/startups", params={"per_page": 101})
        assert response.status_code == 422

    def test_page_0_returns_422(self, seeded_client):
        """page < 1 should return 422"""
        response = seeded_client.get("/startups", params={"page": 0})
        assert response.status_code == 422

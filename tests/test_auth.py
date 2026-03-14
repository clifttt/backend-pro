"""
test_auth.py — Tests for JWT authentication endpoints
Week 12: Unit tests for /token and protected routes
"""
import pytest


# ── /token ──────────────────────────────────────────────────────────────────

class TestTokenEndpoint:
    def test_login_valid_credentials(self, seeded_client):
        """POST /token with correct credentials returns 200 + access_token"""
        response = seeded_client.post(
            "/token",
            data={"username": "admin", "password": "secret"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 10

    def test_login_wrong_password(self, seeded_client):
        """POST /token with wrong password returns 401"""
        response = seeded_client.post(
            "/token",
            data={"username": "admin", "password": "WRONG"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 401

    def test_login_wrong_username(self, seeded_client):
        """POST /token with wrong username returns 401"""
        response = seeded_client.post(
            "/token",
            data={"username": "hacker", "password": "secret"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 401

    def test_login_missing_fields(self, seeded_client):
        """POST /token with no body returns 422 Unprocessable Entity"""
        response = seeded_client.post("/token")
        assert response.status_code == 422

    def test_token_is_valid_jwt_format(self, seeded_client):
        """Token should be a 3-part dot-separated JWT string"""
        response = seeded_client.post(
            "/token",
            data={"username": "admin", "password": "secret"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token = response.json()["access_token"]
        parts = token.split(".")
        assert len(parts) == 3, "JWT must have header.payload.signature"


# ── Protected routes ─────────────────────────────────────────────────────────

class TestProtectedRoutes:
    def test_create_startup_without_token_returns_401(self, seeded_client):
        """POST /startups without auth header → 401"""
        response = seeded_client.post(
            "/startups",
            json={"name": "Unauthorized Startup", "country": "RU"},
        )
        assert response.status_code == 401

    def test_create_startup_with_invalid_token_returns_401(self, seeded_client):
        """POST /startups with garbage token → 401"""
        response = seeded_client.post(
            "/startups",
            json={"name": "Unauthorized Startup", "country": "RU"},
            headers={"Authorization": "Bearer INVALID.TOKEN.HERE"},
        )
        assert response.status_code == 401

    def test_create_startup_with_valid_token_returns_201(
        self, seeded_client, auth_headers
    ):
        """POST /startups with valid JWT → 201 Created"""
        response = seeded_client.post(
            "/startups",
            json={
                "name": "Auth Test Startup",
                "country": "KZ",
                "description": "Created via authenticated request",
                "founded_year": 2023,
                "status": "Active",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        body = response.json()
        assert body["name"] == "Auth Test Startup"
        assert body["country"] == "KZ"
        assert "id" in body

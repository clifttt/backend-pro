"""
test_auth.py — Tests for Auth endpoints (Week 9 + 12)
"""
import pytest


class TestTokenEndpoint:
    def test_login_success(self, seeded_client):
        resp = seeded_client.post(
            "/token",
            data={"username": "admin", "password": "Admin@12345!"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert "expires_in" in body

    def test_login_wrong_password(self, seeded_client):
        resp = seeded_client.post(
            "/token",
            data={"username": "admin", "password": "wrongpassword"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, seeded_client):
        resp = seeded_client.post(
            "/token",
            data={"username": "ghost_user", "password": "whatever123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401

    def test_login_missing_fields(self, seeded_client):
        resp = seeded_client.post(
            "/token",
            data={"username": "admin"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 422


class TestRegisterEndpoint:
    def test_register_new_user(self, seeded_client):
        resp = seeded_client.post(
            "/auth/register",
            json={"username": "newuser_test", "email": "newuser@test.local", "password": "Password123!"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "newuser_test"
        assert "id" in body
        assert "hashed_password" not in body  # never expose

    def test_register_duplicate_username(self, seeded_client):
        # First registration
        seeded_client.post(
            "/auth/register",
            json={"username": "dup_user", "email": "dup1@test.local", "password": "Password123!"},
        )
        # Second with same username
        resp = seeded_client.post(
            "/auth/register",
            json={"username": "dup_user", "email": "dup2@test.local", "password": "Password123!"},
        )
        assert resp.status_code == 409

    def test_register_duplicate_email(self, seeded_client):
        seeded_client.post(
            "/auth/register",
            json={"username": "emailuser1", "email": "shared@test.local", "password": "Password123!"},
        )
        resp = seeded_client.post(
            "/auth/register",
            json={"username": "emailuser2", "email": "shared@test.local", "password": "Password123!"},
        )
        assert resp.status_code == 409

    def test_register_short_password(self, seeded_client):
        resp = seeded_client.post(
            "/auth/register",
            json={"username": "shortpw", "email": "short@test.local", "password": "abc"},
        )
        assert resp.status_code == 422


class TestMeEndpoint:
    def test_get_profile_authenticated(self, seeded_client, auth_headers):
        resp = seeded_client.get("/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "admin"
        assert "email" in body
        assert "is_active" in body
        assert "hashed_password" not in body

    def test_get_profile_unauthenticated(self, seeded_client):
        resp = seeded_client.get("/auth/me")
        assert resp.status_code == 401

    def test_get_profile_invalid_token(self, seeded_client):
        resp = seeded_client.get("/auth/me", headers={"Authorization": "Bearer invalidtoken"})
        assert resp.status_code == 401


class TestSecurityHeaders:
    def test_security_headers_present(self, client):
        resp = client.get("/")
        assert "x-content-type-options" in resp.headers
        assert resp.headers["x-content-type-options"] == "nosniff"
        assert "x-frame-options" in resp.headers
        assert resp.headers["x-frame-options"] == "DENY"
        assert "x-xss-protection" in resp.headers

    def test_protected_endpoint_requires_auth(self, seeded_client):
        resp = seeded_client.post("/startups", json={"name": "Unauthorized Startup"})
        assert resp.status_code == 401

    def test_protected_endpoint_with_valid_token(self, seeded_client, auth_headers):
        resp = seeded_client.post(
            "/startups",
            json={"name": "Auth Test Startup", "country": "US", "founded_year": 2023},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    def test_put_startup_requires_auth(self, seeded_client):
        startups = seeded_client.get("/startups").json()["data"]
        if startups:
            sid = startups[0]["id"]
            resp = seeded_client.put(f"/startups/{sid}", json={"name": "Hack Attempt"})
            assert resp.status_code == 401

    def test_delete_startup_requires_auth(self, seeded_client):
        startups = seeded_client.get("/startups").json()["data"]
        if startups:
            sid = startups[0]["id"]
            resp = seeded_client.delete(f"/startups/{sid}")
            assert resp.status_code == 401

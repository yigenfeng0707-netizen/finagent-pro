import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


pytestmark = pytest.mark.asyncio


class TestAuth:
    async def test_register_success(self, client):
        import uuid as _uuid

        uid = str(_uuid.uuid4())[:8]
        email = f"alice_{uid}@test.com"
        username = f"alice_{uid}"
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": email,
                "username": username,
                "password": "StrongPass1",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == email

    async def test_register_duplicate_email(self, client, registered_user):
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": registered_user["user"]["email"],
                "username": "another",
                "password": "StrongPass1",
            },
        )
        assert resp.status_code == 409

    async def test_register_weak_password(self, client):
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "weak@test.com",
                "username": "weakuser",
                "password": "123",
            },
        )
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client):
        resp = await client.post(
            "/api/auth/register",
            json={
                "email": "not-an-email",
                "username": "bademail",
                "password": "StrongPass1",
            },
        )
        assert resp.status_code == 422

    async def test_login_success(self, client, registered_user):
        email = registered_user["user"]["email"]
        resp = await client.post(
            "/api/auth/login",
            json={
                "email": email,
                "password": "Secure1234",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == email

    async def test_login_wrong_password(self, client, registered_user):
        resp = await client.post(
            "/api/auth/login",
            json={
                "email": registered_user["user"]["email"],
                "password": "WrongPassword1",
            },
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client):
        resp = await client.post(
            "/api/auth/login",
            json={
                "email": "nobody@test.com",
                "password": "SomePass1",
            },
        )
        assert resp.status_code == 401

    async def test_get_me_authenticated(self, client, auth_headers, test_user):
        resp = await client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == test_user.email

    async def test_get_me_unauthenticated(self, client):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_token_refresh(self, client, registered_user):
        refresh_token = registered_user["refresh_token"]
        resp = await client.post(
            "/api/auth/refresh",
            json={
                "refresh_token": refresh_token,
            },
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_logout(self, client, auth_headers):
        resp = await client.post("/api/auth/logout", headers=auth_headers)
        assert resp.status_code == 200

    async def test_rate_limiting(self, client):
        for _ in range(15):
            await client.get("/api/auth/me")
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 429

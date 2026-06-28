"""Tests for authentication endpoints."""

import pytest


@pytest.mark.asyncio
async def test_register_and_login(client):
    """Full registration and login flow."""
    # Register
    resp = await client.post("/auth/register", json={
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepass123",
        "full_name": "Test User",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["username"] == "testuser"

    # Login
    resp2 = await client.post("/auth/login", json={"username": "testuser", "password": "securepass123"})
    assert resp2.status_code == 200
    assert "access_token" in resp2.json()


@pytest.mark.asyncio
async def test_login_invalid_credentials(client, db):
    from backend.db.crud import create_user
    await create_user(db, username="user1", email="u1@x.com", password="pass1")
    await db.commit()

    resp = await client.post("/auth/login", json={"username": "user1", "password": "wrongpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_register_duplicate_username(client):
    payload = {"username": "dup", "email": "a@b.com", "password": "pass"}
    await client.post("/auth/register", json=payload)
    resp = await client.post("/auth/register", json={"username": "dup", "email": "c@d.com", "password": "pass"})
    assert resp.status_code == 400
    assert "taken" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_me(client, auth_headers):
    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


@pytest.mark.asyncio
async def test_get_me_no_auth(client):
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client):
    """Refresh token should yield a new access token."""
    reg = await client.post("/auth/register", json={
        "username": "refreshuser",
        "email": "r@x.com",
        "password": "pass123",
    })
    assert reg.status_code == 200
    refresh = reg.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert "refresh_token" in resp.json()


@pytest.mark.asyncio
async def test_logout(client, auth_headers, admin_token):
    """Logout should invalidate the token."""
    resp = await client.post("/auth/logout", headers=auth_headers)
    assert resp.status_code == 200

    # Using the revoked token should now fail
    resp2 = await client.get("/auth/me", headers=auth_headers)
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_list_users_admin(client, auth_headers):
    resp = await client.get("/auth/users", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_list_users_non_admin(client):
    """Non-admin user should not list all users."""
    reg = await client.post("/auth/register", json={
        "username": "viewer1",
        "email": "v1@x.com",
        "password": "pass",
        "roles": ["viewer"],
    })
    token = reg.json()["access_token"]
    resp = await client.get("/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_api_key_create_and_use(client, auth_headers):
    """Create an API key and use it to authenticate."""
    # Create key
    resp = await client.post(
        "/auth/api-keys",
        json={"name": "test-key"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    key = resp.json()["key"]
    assert key.startswith("qac_")

    # Use key for auth
    resp2 = await client.get("/auth/me", headers={"Authorization": f"Bearer {key}"})
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_api_key_list(client, auth_headers):
    await client.post("/auth/api-keys", json={"name": "key1"}, headers=auth_headers)
    await client.post("/auth/api-keys", json={"name": "key2"}, headers=auth_headers)

    resp = await client.get("/auth/api-keys", headers=auth_headers)
    assert resp.status_code == 200
    keys = resp.json()
    assert len(keys) >= 2


@pytest.mark.asyncio
async def test_api_key_revoke(client, auth_headers):
    resp = await client.post("/auth/api-keys", json={"name": "rev-key"}, headers=auth_headers)
    key_id = resp.json()["id"]
    raw_key = resp.json()["key"]

    # Revoke
    del_resp = await client.delete(f"/auth/api-keys/{key_id}", headers=auth_headers)
    assert del_resp.status_code == 200

    # Revoked key should not authenticate
    resp2 = await client.get("/auth/me", headers={"Authorization": f"Bearer {raw_key}"})
    assert resp2.status_code == 401

"""Shared test fixtures and configuration."""

import sys
import os

# Ensure project root is on sys.path regardless of how pytest is invoked
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.db.session import Base, get_db
from backend.main import app


TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_qa_copilot.db"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db():
    """Fresh database for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestSessionLocal() as session:
        yield session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client():
    """Async HTTP client for the FastAPI app."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def admin_token(client):
    """Get JWT token for admin user. Creates admin if needed."""
    from backend.db.crud import create_user, get_user_by_username
    from backend.config import settings

    async with TestSessionLocal() as session:
        user = await get_user_by_username(session, "admin")
        if not user:
            await create_user(
                session,
                username="admin",
                email="admin@test.com",
                password="adminpass",
                full_name="Test Admin",
                roles=["admin"],
                permissions=["read:queries", "write:queries", "execute:tests",
                             "manage:users", "manage:settings", "view:reports",
                             "export:reports", "admin:access"],
            )
            await session.commit()

    resp = await client.post("/auth/login", json={"username": "admin", "password": "adminpass"})
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}

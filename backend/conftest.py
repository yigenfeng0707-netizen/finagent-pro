"""
Pytest configuration with async fixtures for FastAPI + SQLAlchemy async.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

import pytest
from auth.password import hash_password
from database import Base, get_db
from database.models import User
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    os.getenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:"),
)


@pytest.fixture
async def test_engine():
    """Function-scoped engine to ensure each test gets its own event loop + DB connections.

    默认使用 sqlite+aiosqlite 内存数据库运行测试，无需本地 PostgreSQL。
    生产环境可通过 TEST_DATABASE_URL 环境变量覆盖。
    """
    engine_kwargs = {"echo": False, "pool_pre_ping": True}
    if TEST_DATABASE_URL.startswith("postgresql"):
        engine_kwargs["pool_size"] = 5
    engine = create_async_engine(TEST_DATABASE_URL, **engine_kwargs)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    uid = str(uuid.uuid4())[:8]
    user = User(
        id=uuid.uuid4(),
        email=f"test_{uid}@example.com",
        username=f"testuser_{uid}",
        hashed_password=hash_password("Test1234!"),
        email_verified=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter state between tests to avoid cross-test interference."""
    from middleware import rate_limiter

    rate_limiter.windows.clear()
    yield


@pytest.fixture
async def client(test_engine):
    from main import app

    async def override_get_db():
        session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(client, test_user, db_session):
    from auth.jwt import create_access_token, create_refresh_token
    from database.crud import create_session

    access_token = create_access_token(test_user.id, test_user.role)
    refresh_token = create_refresh_token(test_user.id)
    await create_session(db_session, test_user.id, access_token, refresh_token)
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def registered_user(client) -> dict:
    uid = str(uuid.uuid4())[:8]
    response = await client.post(
        "/api/auth/register",
        json={
            "email": f"reg_{uid}@example.com",
            "username": f"reguser_{uid}",
            "password": "Secure1234",
        },
    )
    assert response.status_code == 201
    return response.json()

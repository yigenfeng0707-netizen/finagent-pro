from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
import os


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://finagent:finagent123@localhost:5432/finagent_pro"
)

_engine = None
_AsyncSessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        kwargs = {"echo": False}
        if DATABASE_URL.startswith("postgresql"):
            kwargs["pool_size"] = 10
            kwargs["max_overflow"] = 20
        _engine = create_async_engine(DATABASE_URL, **kwargs)
    return _engine


def get_session_maker():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

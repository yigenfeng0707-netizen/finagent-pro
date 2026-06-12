import os
from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logger.warning("DATABASE_URL 未配置，使用本地开发默认值。生产环境必须设置此环境变量。")
    DATABASE_URL = "postgresql+asyncpg://finagent:finagent_dev@localhost:5432/finagent_pro"

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

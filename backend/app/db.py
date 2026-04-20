import os
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _get_async_url() -> str:
    """DATABASE_URL을 asyncpg 드라이버용으로 정규화."""
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://agentic:agentic_dev_pw@localhost:5432/agentic_ai",
    )
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


engine = create_async_engine(_get_async_url(), echo=False, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session

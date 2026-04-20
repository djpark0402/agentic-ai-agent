import os
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


def _get_async_url() -> str:
    """DATABASE_URL을 asyncpg 드라이버용으로 정규화."""
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://agentic:agentic_dev_pw@localhost:5432/agentic_ai",
    )
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# NullPool: 테스트의 event loop 간 연결 재사용 문제 회피.
# 개발/프로덕션에서도 요청당 연결 비용은 크지 않고, 향후 필요 시 풀 전략 재평가.
engine = create_async_engine(_get_async_url(), echo=False, future=True, poolclass=NullPool)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        yield session

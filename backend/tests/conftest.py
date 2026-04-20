import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://agentic:agentic_dev_pw@localhost:5432/agentic_ai",
)


@pytest_asyncio.fixture
async def client():
    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.fixture
def session_id() -> str:
    """테스트마다 격리된 session_id — 다른 테스트/실사용 데이터와 섞이지 않음."""
    return f"test-{uuid.uuid4()}"

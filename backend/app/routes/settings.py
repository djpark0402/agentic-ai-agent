import os

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import AppSetting
from ..schemas import AppSettingRead, AppSettingUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])

BASE_URL_KEY = "BASE_URL"
BASE_URL_ENV_DEFAULT = "http://10.47.18.100:8000/v1"


async def get_base_url(session: AsyncSession) -> tuple[str, str]:
    """현재 BASE_URL과 출처("db"|"env")를 반환."""
    row = await session.get(AppSetting, BASE_URL_KEY)
    if row is not None:
        return row.value, "db"
    return os.getenv("BASE_URL", BASE_URL_ENV_DEFAULT), "env"


@router.get("/base_url", response_model=AppSettingRead)
async def read_base_url(session: AsyncSession = Depends(get_session)):
    value, source = await get_base_url(session)
    return AppSettingRead(key=BASE_URL_KEY, value=value, source=source)


@router.put("/base_url", response_model=AppSettingRead)
async def update_base_url(
    payload: AppSettingUpdate, session: AsyncSession = Depends(get_session)
):
    row = await session.get(AppSetting, BASE_URL_KEY)
    if row is None:
        row = AppSetting(key=BASE_URL_KEY, value=payload.value)
        session.add(row)
    else:
        row.value = payload.value
    await session.commit()
    await session.refresh(row)
    return AppSettingRead(key=BASE_URL_KEY, value=row.value, source="db")

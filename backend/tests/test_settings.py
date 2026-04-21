import pytest


@pytest.mark.asyncio
class TestSettingsAPI:
    async def test_get_base_url_falls_back_to_env(self, client, monkeypatch):
        """DB에 값이 없으면 env의 BASE_URL을 반환하고 source='env'."""
        monkeypatch.setenv("BASE_URL", "http://env-default:8000/v1")

        # DB에 혹시 남아있을 수 있는 설정을 초기화
        from sqlalchemy import text
        from app.db import AsyncSessionLocal

        async with AsyncSessionLocal() as s:
            await s.execute(text("DELETE FROM app_settings WHERE key = 'BASE_URL'"))
            await s.commit()

        resp = await client.get("/api/settings/base_url")
        assert resp.status_code == 200
        data = resp.json()
        assert data["key"] == "BASE_URL"
        assert data["value"] == "http://env-default:8000/v1"
        assert data["source"] == "env"

    async def test_put_base_url_persists_and_get_returns_db_value(self, client):
        new_url = "http://updated-host:9000/v1"
        put_resp = await client.put(
            "/api/settings/base_url", json={"value": new_url}
        )
        assert put_resp.status_code == 200
        assert put_resp.json()["value"] == new_url

        get_resp = await client.get("/api/settings/base_url")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["value"] == new_url
        assert data["source"] == "db"

    async def test_put_base_url_rejects_empty_value(self, client):
        resp = await client.put("/api/settings/base_url", json={"value": ""})
        assert resp.status_code == 422

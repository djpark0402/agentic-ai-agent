import pytest


@pytest.mark.asyncio
class TestConversationsAPI:
    async def test_create_conversation_returns_uuid(self, client, session_id):
        resp = await client.post(
            "/api/conversations",
            json={"session_id": session_id, "title": "첫 대화"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["session_id"] == session_id
        assert data["title"] == "첫 대화"

    async def test_list_conversations_scoped_by_session(self, client, session_id):
        other = f"test-other-{session_id}"
        await client.post("/api/conversations", json={"session_id": session_id, "title": "A"})
        await client.post("/api/conversations", json={"session_id": session_id, "title": "B"})
        await client.post("/api/conversations", json={"session_id": other, "title": "X"})

        resp = await client.get("/api/conversations", params={"session_id": session_id})
        assert resp.status_code == 200
        titles = [c["title"] for c in resp.json()]
        assert set(titles) == {"A", "B"}

    async def test_get_messages_returns_empty_for_new_conversation(
        self, client, session_id
    ):
        r = await client.post(
            "/api/conversations", json={"session_id": session_id, "title": "빈 대화"}
        )
        conv_id = r.json()["id"]
        resp = await client.get(f"/api/conversations/{conv_id}/messages")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_delete_conversation_cascades(self, client, session_id):
        r = await client.post(
            "/api/conversations", json={"session_id": session_id, "title": "삭제할 대화"}
        )
        conv_id = r.json()["id"]

        resp = await client.delete(f"/api/conversations/{conv_id}")
        assert resp.status_code == 204

        # 목록에서도 사라짐
        lst = await client.get("/api/conversations", params={"session_id": session_id})
        assert all(c["id"] != conv_id for c in lst.json())

    async def test_chat_with_conversation_id_persists_messages(
        self, client, session_id, monkeypatch
    ):
        """chat 엔드포인트가 conversation_id를 받으면 user/assistant 메시지를 DB에 저장해야 한다."""

        async def _fake_stream(messages, system, model=None):
            yield {"type": "status", "stage": "thinking", "label": "..."}
            yield {"type": "token", "content": "안녕"}
            yield {"type": "token", "content": "하세요"}
            yield {"type": "done"}

        from app import main as main_mod

        monkeypatch.setattr(main_mod, "stream_events", _fake_stream)

        r = await client.post(
            "/api/conversations", json={"session_id": session_id, "title": "chat test"}
        )
        conv_id = r.json()["id"]

        resp = await client.post(
            "/api/chat",
            json={
                "conversation_id": conv_id,
                "messages": [{"role": "user", "content": "안녕"}],
                "system": "You are a helpful assistant.",
            },
        )
        assert resp.status_code == 200
        # 스트림 소진
        async for _ in resp.aiter_lines():
            pass

        msgs = (await client.get(f"/api/conversations/{conv_id}/messages")).json()
        roles = [m["role"] for m in msgs]
        assert roles == ["user", "assistant"]
        assert msgs[0]["content"] == "안녕"
        assert msgs[1]["content"] == "안녕하세요"

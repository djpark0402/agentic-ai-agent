import json

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_session
from .llm import stream_events
from .models import Conversation, Message
from .routes.conversations import router as conversations_router
from .schemas import ChatRequest

# 최근 N턴만 LLM에 전달하는 슬라이딩 윈도우 크기 (user/assistant 메시지 합계 기준)
HISTORY_WINDOW = 20

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(req: ChatRequest, session: AsyncSession = Depends(get_session)):
    # 대화 저장: conversation_id가 있으면 user 메시지를 DB에 기록하고
    # DB의 기존 이력(최근 HISTORY_WINDOW턴) + 새 user 메시지를 LLM에 전달
    conv: Conversation | None = None
    messages_for_llm = req.messages
    if req.conversation_id is not None:
        conv = await session.get(Conversation, req.conversation_id)
        if conv is None:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="conversation not found")

        last_user = req.messages[-1] if req.messages else None
        if last_user is not None and last_user.role == "user":
            session.add(
                Message(
                    conversation_id=conv.id,
                    role="user",
                    content=last_user.content,
                )
            )
            await session.commit()

        # DB에서 최근 HISTORY_WINDOW개의 메시지를 가져와 LLM 입력 구성
        from sqlmodel import select

        stmt = (
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(HISTORY_WINDOW)
        )
        result = await session.execute(stmt)
        recent = list(reversed(result.scalars().all()))
        from .schemas import Message as MessageSchema

        messages_for_llm = [
            MessageSchema(role=m.role, content=m.content) for m in recent
        ]

    async def event_stream():
        full_reply = ""
        try:
            async for ev in stream_events(messages_for_llm, req.system, req.model):
                if ev.get("type") == "token":
                    full_reply += ev.get("content", "")
                yield f"data: {json.dumps(ev, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
            return

        if conv is not None and full_reply:
            session.add(
                Message(
                    conversation_id=conv.id,
                    role="assistant",
                    content=full_reply,
                )
            )
            await session.commit()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
